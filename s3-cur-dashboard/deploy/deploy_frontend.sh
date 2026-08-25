#!/usr/bin/env bash
# Build the frontend, sync it to a private S3 bucket, and serve both the
# frontend AND the backend API from one CloudFront distribution over HTTPS:
# the default behavior serves the frontend from S3, and a /api/* behavior
# forwards to the backend Lambda's Function URL. Both origins use Origin
# Access Control, so CloudFront signs requests to each on the distribution's
# behalf -- neither the S3 bucket nor the Lambda Function URL needs a public
# ("Principal": "*") resource policy. (Some AWS Organizations block public
# resource policies outright as a guardrail, which a bare public Function
# URL would run into; this avoids that entirely, and also means the
# frontend calls the API same-origin -- no CORS needed.)
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

echo "== Looking up the Lambda Function URL =="
LAMBDA_FUNCTION_URL="$(aws lambda get-function-url-config --function-name "$LAMBDA_FUNCTION_NAME" --region "$AWS_REGION" --query 'FunctionUrl' --output text)"
LAMBDA_DOMAIN="$(echo "$LAMBDA_FUNCTION_URL" | sed -E 's#^https://##; s#/$##')"
LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${LAMBDA_FUNCTION_NAME}"

echo "== Installing dependencies =="
(cd "$FRONTEND_DIR" && npm install)

echo "== Building (API calls are same-origin via /api/*, no base URL needed) =="
(cd "$FRONTEND_DIR" && VITE_API_KEY="$API_KEY" npm run build)

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

echo "== Ensuring Lambda Origin Access Control exists =="
LAMBDA_OAC_ID="$(aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='${LAMBDA_FUNCTION_NAME}-oac'].Id | [0]" --output text)"
if [ -z "$LAMBDA_OAC_ID" ] || [ "$LAMBDA_OAC_ID" = "None" ]; then
  LAMBDA_OAC_ID="$(aws cloudfront create-origin-access-control --origin-access-control-config \
    "Name=${LAMBDA_FUNCTION_NAME}-oac,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=lambda" \
    --query 'OriginAccessControl.Id' --output text)"
fi

echo "== Ensuring CloudFront distribution exists =="
DIST_ID="$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?DomainName=='${BUCKET_DOMAIN}']].Id | [0]" --output text)"

if [ -z "$DIST_ID" ] || [ "$DIST_ID" = "None" ]; then
  DIST_CONFIG="$(python3 "$SCRIPT_DIR/build_distribution_config.py" create \
    "$BUCKET" "$BUCKET_DOMAIN" "$S3_OAC_ID" "$LAMBDA_DOMAIN" "$LAMBDA_OAC_ID" "$DOMAIN_NAME" "$ACM_CERT_ARN")"
  CREATE_RESULT="$(aws cloudfront create-distribution --distribution-config "$DIST_CONFIG")"
  DIST_ID="$(echo "$CREATE_RESULT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["Distribution"]["Id"])')"
  echo "Created distribution $DIST_ID -- first-time edge propagation can take up to ~15 minutes."
else
  echo "== Wiring the Lambda origin / custom domain into the existing distribution =="
  CURRENT="$(aws cloudfront get-distribution-config --id "$DIST_ID")"
  ETAG="$(echo "$CURRENT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["ETag"])')"
  MERGED_CONFIG="$(echo "$CURRENT" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["DistributionConfig"]))' \
    | python3 "$SCRIPT_DIR/build_distribution_config.py" merge "$LAMBDA_DOMAIN" "$LAMBDA_OAC_ID" "$DOMAIN_NAME" "$ACM_CERT_ARN")"
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

echo "== Restricting the Lambda Function URL to this distribution only =="
ADD_PERMISSION_OUTPUT="$(aws lambda add-permission \
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --statement-id "AllowCloudFront${DIST_ID}" \
  --action lambda:InvokeFunctionUrl \
  --principal cloudfront.amazonaws.com \
  --source-arn "$DIST_ARN" \
  --function-url-auth-type AWS_IAM \
  --region "$AWS_REGION" 2>&1)" || {
    if ! echo "$ADD_PERMISSION_OUTPUT" | grep -q "ResourceConflictException"; then
      echo "$ADD_PERMISSION_OUTPUT" >&2
      exit 1
    fi
    echo "(already granted on a prior run)"
  }

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
needed. The dashboard calls its own API at /api/* on this same domain, so
there's nothing further to configure. To use your own domain, get a
certificate imported/issued into ACM in us-east-1 (see
import_certificate.sh for an existing cert/key) and re-run this script
with DOMAIN_NAME and ACM_CERT_ARN set.
EOF
fi
