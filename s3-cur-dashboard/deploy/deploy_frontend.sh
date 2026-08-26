#!/usr/bin/env bash
# Build the frontend, sync it to a private S3 bucket, and serve it from a
# CloudFront distribution over HTTPS.
#
# The frontend calls the backend two different ways depending on the call:
# - /api/health (fast) goes through this same CloudFront distribution's
#   /api/* behavior to the API Gateway HTTP API deploy_backend.sh creates.
#   The S3 origin uses Origin Access Control (no public bucket policy
#   needed); the API Gateway origin is a plain public custom origin
#   (API Gateway's default endpoint is already public) -- access control
#   there is the app-level CUR_DASHBOARD_API_KEY (see require_api_key in
#   main.py), not IAM signing.
# - /api/cur/load (slow -- a real CUR export can take minutes) is called
#   DIRECTLY against the Lambda's Function URL, bypassing CloudFront and
#   API Gateway entirely, because API Gateway's 30-second integration
#   timeout is hard and not configurable, and a real 151-part CUR export
#   already blew past it. A Function URL called directly has no such
#   ceiling. This is baked into the frontend build via VITE_API_BASE_URL.
#
# (An earlier version of this script routed /api/* -- including the load
# call -- to the Lambda's Function URL via CloudFront + a second Origin
# Access Control. That combination -- CloudFront's OAC signing requests to
# a Lambda Function URL origin -- reproducibly returned Forbidden in this
# AWS account despite matching AWS's documented config exactly (verified
# with a direct SigV4-signed request to the same URL, which succeeded).
# Calling the Function URL directly, with no CloudFront/OAC/signing
# involved at all, is a different code path from that failure.)
#
# CloudFront's free tier (1TB transfer + 10M requests per month) is
# permanent, so this stays $0 at low traffic; PriceClass_100 restricts edge
# locations to the cheapest tier (US/Canada/Europe) since cost, not global
# latency, is the priority here.
#
# Usage:
#   LAMBDA_FUNCTION_NAME=cur-dashboard-backend BUCKET=my-cur-dashboard-frontend ./deploy_frontend.sh
#
# Optional custom domain (both must be set together):
#   DOMAIN_NAME=cur.example.com ACM_CERT_ARN=arn:aws:acm:us-east-1:...:certificate/... ./deploy_frontend.sh
# The ACM certificate must already exist in us-east-1 -- CloudFront requires
# that region regardless of the distribution's own edge locations. Use
# import_certificate.sh if you have an existing cert/key rather than one
# ACM can issue and DNS-validate itself.
set -euo pipefail

: "${LAMBDA_FUNCTION_NAME:?Set LAMBDA_FUNCTION_NAME to the backend Lambda function name}"
: "${BUCKET:?Set BUCKET to the S3 bucket to host the frontend from}"
AWS_REGION="${AWS_REGION:-us-east-1}"
API_KEY="${API_KEY:-}"
DOMAIN_NAME="${DOMAIN_NAME:-}"
ACM_CERT_ARN="${ACM_CERT_ARN:-}"
if { [ -n "$DOMAIN_NAME" ] && [ -z "$ACM_CERT_ARN" ]; } || { [ -z "$DOMAIN_NAME" ] && [ -n "$ACM_CERT_ARN" ]; }; then
  echo "DOMAIN_NAME and ACM_CERT_ARN must be set together" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"
BUCKET_DOMAIN="${BUCKET}.s3.${AWS_REGION}.amazonaws.com"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

echo "== Looking up the API Gateway HTTP API endpoint =="
API_NAME="${API_NAME:-${LAMBDA_FUNCTION_NAME}-api}"
API_ID="$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
  --query "Items[?Name=='${API_NAME}'].ApiId | [0]" --output text)"
if [ -z "$API_ID" ] || [ "$API_ID" = "None" ]; then
  echo "No API Gateway HTTP API named '${API_NAME}' found -- run deploy_backend.sh first." >&2
  exit 1
fi
API_ENDPOINT="$(aws apigatewayv2 get-api --api-id "$API_ID" --region "$AWS_REGION" --query 'ApiEndpoint' --output text)"
API_DOMAIN="$(echo "$API_ENDPOINT" | sed -E 's#^https://##; s#/$##')"

echo "== Looking up the Lambda Function URL (used directly for the slow /api/cur/load call) =="
FUNCTION_URL="$(aws lambda get-function-url-config --function-name "$LAMBDA_FUNCTION_NAME" --region "$AWS_REGION" --query 'FunctionUrl' --output text 2>/dev/null || true)"
if [ -z "$FUNCTION_URL" ] || [ "$FUNCTION_URL" = "None" ]; then
  echo "No Function URL found on $LAMBDA_FUNCTION_NAME -- run deploy_backend.sh first." >&2
  exit 1
fi
FUNCTION_URL="${FUNCTION_URL%/}"  # strip the trailing slash AWS always includes -- api.ts appends /api/cur/load itself

echo "== Installing dependencies =="
(cd "$FRONTEND_DIR" && npm install)

echo "== Building (/api/health same-origin via /api/*, /api/cur/load direct to the Function URL) =="
(cd "$FRONTEND_DIR" && VITE_API_KEY="$API_KEY" VITE_API_BASE_URL="$FUNCTION_URL" npm run build)

echo "== Ensuring bucket exists (private -- CloudFront reads it, the public internet does not) =="
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION" \
    $( [ "$AWS_REGION" != "us-east-1" ] && echo "--create-bucket-configuration LocationConstraint=$AWS_REGION" )
fi
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "== Syncing build output =="
aws s3 sync "$FRONTEND_DIR/dist" "s3://$BUCKET" --delete

echo "== Ensuring S3 Origin Access Control exists =="
S3_OAC_ID="$(aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='${BUCKET}-oac'].Id | [0]" --output text)"
if [ -z "$S3_OAC_ID" ] || [ "$S3_OAC_ID" = "None" ]; then
  S3_OAC_ID="$(aws cloudfront create-origin-access-control --origin-access-control-config \
    "Name=${BUCKET}-oac,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3" \
    --query 'OriginAccessControl.Id' --output text)"
fi

echo "== Ensuring CloudFront distribution exists =="
DIST_ID="$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?DomainName=='${BUCKET_DOMAIN}']].Id | [0]" --output text)"

if [ -z "$DIST_ID" ] || [ "$DIST_ID" = "None" ]; then
  DIST_CONFIG="$(python3 "$SCRIPT_DIR/build_distribution_config.py" create \
    "$BUCKET" "$BUCKET_DOMAIN" "$S3_OAC_ID" "$API_DOMAIN" "$DOMAIN_NAME" "$ACM_CERT_ARN")"
  CREATE_RESULT="$(aws cloudfront create-distribution --distribution-config "$DIST_CONFIG")"
  DIST_ID="$(echo "$CREATE_RESULT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["Distribution"]["Id"])')"
  echo "Created distribution $DIST_ID -- first-time edge propagation can take up to ~15 minutes."
else
  echo "== Wiring the API Gateway origin / custom domain into the existing distribution =="
  CURRENT="$(aws cloudfront get-distribution-config --id "$DIST_ID")"
  ETAG="$(echo "$CURRENT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["ETag"])')"
  MERGED_CONFIG="$(echo "$CURRENT" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["DistributionConfig"]))' \
    | python3 "$SCRIPT_DIR/build_distribution_config.py" merge "$API_DOMAIN" "$DOMAIN_NAME" "$ACM_CERT_ARN")"
  aws cloudfront update-distribution --id "$DIST_ID" --if-match "$ETAG" --distribution-config "$MERGED_CONFIG" >/dev/null
  echo "== Invalidating cache so the new build is served immediately =="
  aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" >/dev/null
fi

DIST_ARN="arn:aws:cloudfront::${ACCOUNT_ID}:distribution/${DIST_ID}"
DIST_DOMAIN="$(aws cloudfront get-distribution --id "$DIST_ID" --query 'Distribution.DomainName' --output text)"

echo "== Restricting the S3 bucket to this distribution only =="
BUCKET_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontServicePrincipal",
      "Effect": "Allow",
      "Principal": { "Service": "cloudfront.amazonaws.com" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET}/*",
      "Condition": { "StringEquals": { "AWS:SourceArn": "${DIST_ARN}" } }
    }
  ]
}
EOF
)
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "$BUCKET_POLICY"

# No equivalent restriction needed on the API Gateway origin: it's already
# public (access control is the app-level API key, not IAM/OAC), and
# deploy_backend.sh's quick-create already granted API Gateway permission
# to invoke the Lambda function.

if [ -n "$DOMAIN_NAME" ]; then
  cat <<EOF

Frontend + API deployed.

  https://${DOMAIN_NAME}   (once DNS is pointed below)
  https://${DIST_DOMAIN}   (works immediately)

On your DNS provider, add a CNAME record:

  ${DOMAIN_NAME}  ->  ${DIST_DOMAIN}

(If ${DOMAIN_NAME} is a bare apex domain, most DNS providers require an
ALIAS/ANAME record instead of CNAME at the apex -- use that record type
pointed at the same target.)
EOF
else
  cat <<EOF

Frontend + API deployed.

  https://${DIST_DOMAIN}

HTTPS via CloudFront's default certificate for that domain -- no ACM setup
needed. The dashboard calls /api/health same-origin and /api/cur/load
directly against ${FUNCTION_URL} -- both already baked into this build,
nothing further to configure. To use your own domain, get a
certificate imported/issued into ACM in us-east-1 (see
import_certificate.sh for an existing cert/key) and re-run this script
with DOMAIN_NAME and ACM_CERT_ARN set.
EOF
fi
