#!/usr/bin/env bash
# Build the frontend against a deployed backend URL and sync it to an S3
# bucket configured for static website hosting -- storage + requests for a
# ~150KB bundle at low traffic round to $0.
#
# Plain S3 website hosting serves over HTTP only. Put CloudFront in front of
# it (free tier covers most low-traffic use) once you want HTTPS/a custom
# domain -- not included here to keep this scaffold to one moving part.
#
# Usage: API_BASE_URL=https://xxxx.lambda-url.us-east-1.on.aws BUCKET=my-cur-dashboard-frontend ./deploy_frontend.sh
set -euo pipefail

: "${API_BASE_URL:?Set API_BASE_URL to the backend Lambda Function URL}"
: "${BUCKET:?Set BUCKET to the S3 bucket to host the frontend from}"
AWS_REGION="${AWS_REGION:-us-east-1}"
API_KEY="${API_KEY:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"

echo "== Installing dependencies =="
(cd "$FRONTEND_DIR" && npm install)

echo "== Building =="
(cd "$FRONTEND_DIR" && VITE_API_BASE_URL="$API_BASE_URL" VITE_API_KEY="$API_KEY" npm run build)

echo "== Ensuring bucket exists and is configured for static website hosting =="
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION" \
    $( [ "$AWS_REGION" != "us-east-1" ] && echo "--create-bucket-configuration LocationConstraint=$AWS_REGION" )
fi
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
aws s3 website "s3://$BUCKET" --index-document index.html --error-document index.html
POLICY=$(cat <<EOF
{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::${BUCKET}/*"}]}
EOF
)
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "$POLICY"

echo "== Syncing build output =="
aws s3 sync "$FRONTEND_DIR/dist" "s3://$BUCKET" --delete

cat <<EOF

Frontend deployed.

  http://${BUCKET}.s3-website-${AWS_REGION}.amazonaws.com

This is plain HTTP. Add CloudFront in front of the bucket for HTTPS and a
custom domain once you're ready for that.
EOF
