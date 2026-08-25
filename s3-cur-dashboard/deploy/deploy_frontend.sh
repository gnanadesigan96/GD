#!/usr/bin/env bash
# Build the frontend against a deployed backend URL, sync it to a private S3
# bucket, and serve it over HTTPS through CloudFront (using Origin Access
# Control so only CloudFront -- not the public internet -- can read the
# bucket directly). CloudFront's free tier (1TB transfer + 10M requests per
# month) is permanent, so this stays $0 at low traffic; PriceClass_100
# restricts edge locations to the cheapest tier (US/Canada/Europe) since
# cost, not global latency, is the priority here.
#
# Usage: API_BASE_URL=https://xxxx.lambda-url.us-east-1.on.aws BUCKET=my-cur-dashboard-frontend ./deploy_frontend.sh
set -euo pipefail

: "${API_BASE_URL:?Set API_BASE_URL to the backend Lambda Function URL}"
: "${BUCKET:?Set BUCKET to the S3 bucket to host the frontend from}"
AWS_REGION="${AWS_REGION:-us-east-1}"
API_KEY="${API_KEY:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"
BUCKET_DOMAIN="${BUCKET}.s3.${AWS_REGION}.amazonaws.com"

echo "== Installing dependencies =="
(cd "$FRONTEND_DIR" && npm install)

echo "== Building =="
(cd "$FRONTEND_DIR" && VITE_API_BASE_URL="$API_BASE_URL" VITE_API_KEY="$API_KEY" npm run build)

echo "== Ensuring bucket exists (private -- CloudFront reads it, the public internet does not) =="
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION" \
    $( [ "$AWS_REGION" != "us-east-1" ] && echo "--create-bucket-configuration LocationConstraint=$AWS_REGION" )
fi
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "== Syncing build output =="
aws s3 sync "$FRONTEND_DIR/dist" "s3://$BUCKET" --delete

echo "== Ensuring Origin Access Control exists =="
OAC_ID="$(aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='${BUCKET}-oac'].Id | [0]" --output text)"
if [ -z "$OAC_ID" ] || [ "$OAC_ID" = "None" ]; then
  OAC_ID="$(aws cloudfront create-origin-access-control --origin-access-control-config \
    "Name=${BUCKET}-oac,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3" \
    --query 'OriginAccessControl.Id' --output text)"
fi

echo "== Ensuring CloudFront distribution exists =="
DIST_ID="$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[0].DomainName=='${BUCKET_DOMAIN}'].Id | [0]" --output text)"

if [ -z "$DIST_ID" ] || [ "$DIST_ID" = "None" ]; then
  DIST_CONFIG=$(cat <<EOF
{
  "CallerReference": "${BUCKET}-frontend",
  "Comment": "S3 CUR dashboard frontend",
  "Enabled": true,
  "PriceClass": "PriceClass_100",
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "s3-origin",
        "DomainName": "${BUCKET_DOMAIN}",
        "S3OriginConfig": { "OriginAccessIdentity": "" },
        "OriginAccessControlId": "${OAC_ID}"
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "s3-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"] },
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6"
  },
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      { "ErrorCode": 403, "ResponseCode": "200", "ResponsePagePath": "/index.html" },
      { "ErrorCode": 404, "ResponseCode": "200", "ResponsePagePath": "/index.html" }
    ]
  }
}
EOF
)
  CREATE_RESULT="$(aws cloudfront create-distribution --distribution-config "$DIST_CONFIG")"
  DIST_ID="$(echo "$CREATE_RESULT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["Distribution"]["Id"])')"
  echo "Created distribution $DIST_ID -- first-time edge propagation can take up to ~15 minutes."
else
  echo "== Invalidating cache so the new build is served immediately =="
  aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" >/dev/null
fi

DIST_ARN="arn:aws:cloudfront::$(aws sts get-caller-identity --query Account --output text):distribution/${DIST_ID}"
DIST_DOMAIN="$(aws cloudfront get-distribution --id "$DIST_ID" --query 'Distribution.DomainName' --output text)"

echo "== Restricting the bucket to this distribution only =="
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

cat <<EOF

Frontend deployed.

  https://${DIST_DOMAIN}

HTTPS via CloudFront's default certificate for that domain -- no ACM setup
needed. To use your own domain instead, add an ACM certificate (in
us-east-1) and an alias record pointing at ${DIST_DOMAIN}, then update the
distribution with Aliases + ViewerCertificate.
EOF
