#!/usr/bin/env bash
# Build the backend as a container image, push it to ECR, and create/update
# the Lambda function + a public Function URL (no API Gateway -- Function
# URLs have no extra cost beyond Lambda itself).
#
# Requires: docker, aws cli v2, credentials with permission to manage ECR,
# Lambda, and IAM in the target account/region.
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
docker build -t "${ECR_REPO_NAME}:${IMAGE_TAG}" "$BACKEND_DIR"
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

echo "== Ensuring Function URL exists =="
if ! aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws lambda create-function-url-config \
    --function-name "$FUNCTION_NAME" \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["*"],"AllowHeaders":["content-type","x-api-key"]}' \
    --region "$AWS_REGION" >/dev/null
  aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id FunctionURLAllowPublicAccess \
    --action lambda:InvokeFunctionUrl \
    --principal '*' \
    --function-url-auth-type NONE \
    --region "$AWS_REGION" >/dev/null
fi

FUNCTION_URL="$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'FunctionUrl' --output text)"

cat <<EOF

Backend deployed.

  Function URL: ${FUNCTION_URL}

Set CUR_DASHBOARD_API_KEY on the function (and the matching VITE_API_KEY
when building the frontend) before pointing real users at this URL --
AuthType=NONE means anyone with the URL can invoke it otherwise:

  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" \\
    --environment "Variables={CUR_DASHBOARD_API_KEY=<a-random-secret>}" \\
    --region "$AWS_REGION"

Set the Azure Key Vault / AWS caller-identity env vars the same way -- see
backend/.env.example for the full list.
EOF
