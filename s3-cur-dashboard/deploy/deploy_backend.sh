#!/usr/bin/env bash
# Build the backend as a container image, push it to ECR, and create/update
# the Lambda function + an API Gateway HTTP API in front of it.
#
# Why API Gateway and not a Function URL: a Function URL with
# AuthType=NONE needs a public (Principal:"*") resource policy, which this
# account's setup rejected outright with Forbidden. Switching to
# AuthType=AWS_IAM + CloudFront Origin Access Control (the documented fix
# for exactly that problem) still failed the same way -- confirmed by a
# controlled test: a genuinely SigV4-signed request straight to the
# Function URL succeeded, but CloudFront's OAC-signed request to the same
# URL did not, isolating the fault to CloudFront's OAC support for Lambda
# Function URL origins in this account, not anything in this script's
# config. API Gateway's Lambda proxy integration is a much older, more
# battle-tested path that sidesteps that failure entirely -- the actual
# access control is the app-level CUR_DASHBOARD_API_KEY (see main.py)
# rather than IAM signing.
#
# Requires: docker, aws cli v2, credentials with permission to manage ECR,
# Lambda, API Gateway, and IAM in the target account/region.
#
# Usage: AWS_REGION=us-east-1 ./deploy_backend.sh
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="${FUNCTION_NAME:-cur-dashboard-backend}"
ECR_REPO_NAME="${ECR_REPO_NAME:-cur-dashboard-backend}"
ROLE_NAME="${ROLE_NAME:-cur-dashboard-lambda-role}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
MEMORY_MB="${MEMORY_MB:-2048}"     # more memory = more vCPU = faster DuckDB parallel scans
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "== Ensuring ECR repo exists =="
aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$ECR_REPO_NAME" --region "$AWS_REGION" >/dev/null

echo "== Applying ECR lifecycle policy (auto-expire old images) =="
# Rule 1: an untagged image only exists because a later push moved a tag
# (e.g. "latest") off it -- nothing references it anymore, so drop it
# quickly. Rule 2: cap total stored images regardless of tag, in case this
# is ever run with unique per-deploy tags instead of reusing IMAGE_TAG.
# Without this, ECR storage cost grows by one image on every deploy.
LIFECYCLE_POLICY='{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire untagged images after 1 day",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 1
      },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 2,
      "description": "Keep only the most recent 5 images total",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 5
      },
      "action": { "type": "expire" }
    }
  ]
}'
aws ecr put-lifecycle-policy \
  --repository-name "$ECR_REPO_NAME" \
  --lifecycle-policy-text "$LIFECYCLE_POLICY" \
  --region "$AWS_REGION" >/dev/null

echo "== Building image =="
# --platform linux/amd64: Lambda create-function defaults to the x86_64
# architecture below (no --architectures flag), so the image must match --
# without this, building on an Apple Silicon Mac produces an arm64 image
# Lambda would reject as a mismatch.
# --provenance=false --sbom=false: modern Docker/BuildKit attaches OCI
# attestation manifests by default, which Lambda's container image support
# does not understand ("image manifest ... not supported"). Disabling them
# keeps the image in the plain Docker manifest format Lambda expects.
docker build --platform linux/amd64 --provenance=false --sbom=false \
  -t "${ECR_REPO_NAME}:${IMAGE_TAG}" "$BACKEND_DIR"
docker tag "${ECR_REPO_NAME}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"

echo "== Pushing image =="
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker push "${ECR_URI}:${IMAGE_TAG}"

echo "== Ensuring Lambda execution role exists =="
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  TRUST_POLICY='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document "$TRUST_POLICY" >/dev/null
  aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole >/dev/null
  echo "Waiting for IAM role propagation..."
  sleep 10
fi
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)"

echo "== Creating or updating Lambda function =="
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --image-uri "${ECR_URI}:${IMAGE_TAG}" \
    --region "$AWS_REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --memory-size "$MEMORY_MB" \
    --timeout "$TIMEOUT_SECONDS" \
    --region "$AWS_REGION" >/dev/null
else
  aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --package-type Image \
    --code "ImageUri=${ECR_URI}:${IMAGE_TAG}" \
    --role "$ROLE_ARN" \
    --memory-size "$MEMORY_MB" \
    --timeout "$TIMEOUT_SECONDS" \
    --region "$AWS_REGION" >/dev/null
  aws lambda wait function-active --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
fi

API_NAME="${API_NAME:-${FUNCTION_NAME}-api}"

echo "== Ensuring API Gateway HTTP API exists (quick-create, Lambda proxy) =="
# Quick-create wires a default $default route/stage AND grants API Gateway
# permission to invoke the function -- no separate add-permission step
# needed, unlike the old Function URL approach.
API_ID="$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
  --query "Items[?Name=='${API_NAME}'].ApiId | [0]" --output text)"

if [ "$API_ID" = "None" ] || [ -z "$API_ID" ]; then
  LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"
  API_ID="$(aws apigatewayv2 create-api \
    --name "$API_NAME" \
    --protocol-type HTTP \
    --target "$LAMBDA_ARN" \
    --region "$AWS_REGION" \
    --query 'ApiId' --output text)"
  echo "Created API Gateway HTTP API: $API_ID"
else
  echo "API Gateway HTTP API already exists: $API_ID"
fi

API_ENDPOINT="$(aws apigatewayv2 get-api --api-id "$API_ID" --region "$AWS_REGION" --query 'ApiEndpoint' --output text)"

cat <<EOF

Backend deployed.

  API endpoint: ${API_ENDPOINT}
  (public, but every route requires the app-level CUR_DASHBOARD_API_KEY --
  see require_api_key in main.py; this replaced a Function URL + CloudFront
  OAC approach that AWS confirmed does not work for Lambda origins in this
  account -- see the comment at the top of this script)

Next: run deploy_frontend.sh with LAMBDA_FUNCTION_NAME=$FUNCTION_NAME --
it wires this API Gateway endpoint into the same CloudFront distribution
as the frontend as the /api/* origin.

Set CUR_DASHBOARD_CALLER_ACCESS_KEY_ID / _SECRET_ACCESS_KEY (or Azure Key
Vault) on the function so it can actually assume customer roles -- see
backend/.env.example for the full list:

  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" \\
    --environment "Variables={CUR_DASHBOARD_CALLER_ACCESS_KEY_ID=<...>,CUR_DASHBOARD_CALLER_SECRET_ACCESS_KEY=<...>}" \\
    --region "$AWS_REGION"

Set CUR_DASHBOARD_API_KEY on the function too, and pass the same value as
API_KEY to deploy_frontend.sh, so the frontend's requests are accepted:

  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" \\
    --environment "Variables={CUR_DASHBOARD_API_KEY=<...>}" \\
    --region "$AWS_REGION"
EOF
