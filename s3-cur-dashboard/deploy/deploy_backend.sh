#!/usr/bin/env bash
# Build the backend as a container image, push it to ECR, and create/update
# the Lambda function + both an API Gateway HTTP API and a public Function
# URL in front of it.
#
# Why both: API Gateway's Lambda proxy integration is the reliable general
# path in this account (see below for why a *CloudFront-fronted* Function
# URL specifically doesn't work here) -- but API Gateway's 30-second
# integration timeout is hard and not configurable. A real customer CUR
# export (151 part files) blew past even Lambda's own 120s timeout, so
# large loads need a call path with no 30-second ceiling. A Function URL
# called directly (no CloudFront in front of it) has no such ceiling --
# only the Lambda's own --timeout applies, which is why that's now set to
# Lambda's max (900s). The frontend calls the Function URL directly for
# /api/cur/load (the slow one) and can keep using either path for
# /api/health.
#
# Why not route everything through a CloudFront-fronted Function URL
# instead of API Gateway: AuthType=AWS_IAM + CloudFront Origin Access
# Control (the documented pattern for that) failed in this account --
# confirmed by a controlled test: a genuinely SigV4-signed request straight
# to the Function URL succeeded, but CloudFront's OAC-signed request to the
# same URL did not, isolating the fault to CloudFront's OAC support for
# Lambda Function URL origins specifically, not anything in this script's
# config. That's a different code path from calling the Function URL
# directly (no CloudFront, no OAC, no signing at all) -- this script's
# AuthType=NONE Function URL relies on the app-level CUR_DASHBOARD_API_KEY
# for access control (see main.py) instead of IAM signing, same as the API
# Gateway path already does.
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
MEMORY_MB="${MEMORY_MB:-4096}"     # more memory = more vCPU = faster DuckDB parallel scans; a real (small) test account's one-month ZIP-CUR export alone used 1.4GB RSS decompressing 3 part files, so 2048 left too little headroom
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-900}"  # Lambda's max -- a real 151-part CUR export already timed out at the old 120s default
EPHEMERAL_STORAGE_MB="${EPHEMERAL_STORAGE_MB:-10240}"  # max Lambda allows (10GB) -- the same real test hit "No space left on device" at 1024MB from just 3 extracted part files; a full month for a busier account, or ZIP-compressed CUR in general, can need much more /tmp than the 512MB default

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
    --ephemeral-storage "Size=${EPHEMERAL_STORAGE_MB}" \
    --region "$AWS_REGION" >/dev/null
else
  aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --package-type Image \
    --code "ImageUri=${ECR_URI}:${IMAGE_TAG}" \
    --role "$ROLE_ARN" \
    --memory-size "$MEMORY_MB" \
    --timeout "$TIMEOUT_SECONDS" \
    --ephemeral-storage "Size=${EPHEMERAL_STORAGE_MB}" \
    --region "$AWS_REGION" >/dev/null
  aws lambda wait function-active --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
fi

API_NAME="${API_NAME:-${FUNCTION_NAME}-api}"

echo "== Ensuring API Gateway HTTP API exists (quick-create, Lambda proxy) =="
LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"
API_ID="$(aws apigatewayv2 get-apis --region "$AWS_REGION" \
  --query "Items[?Name=='${API_NAME}'].ApiId | [0]" --output text)"

if [ "$API_ID" = "None" ] || [ -z "$API_ID" ]; then
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

echo "== Ensuring API Gateway has permission to invoke the function =="
# --target on create-api is documented to auto-grant this, but in this
# account it didn't -- confirmed by `get-policy` returning
# ResourceNotFoundException after a fresh quick-create, which surfaced as a
# generic 500 with the request never reaching Lambda at all (no log
# entries). Granting it explicitly here makes this reliable regardless.
# The source ARN is deliberately just "<api-id>/*" (not the three-segment
# ".../*/*/*" pattern REST APIs use): HTTP APIs invoke through the
# $default stage as "<api-id>/$default/$default" -- only two segments --
# so a three-wildcard pattern never matches and silently blocks the
# invoke.
ADD_PERMISSION_OUTPUT="$(aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/*" \
  --region "$AWS_REGION" 2>&1)" || {
    if ! echo "$ADD_PERMISSION_OUTPUT" | grep -q "ResourceConflictException"; then
      echo "$ADD_PERMISSION_OUTPUT" >&2
      exit 1
    fi
    echo "(already granted on a prior run)"
  }

API_ENDPOINT="$(aws apigatewayv2 get-api --api-id "$API_ID" --region "$AWS_REGION" --query 'ApiEndpoint' --output text)"

echo "== Ensuring Function URL exists (AuthType=NONE, for calls with no 30s ceiling) =="
if ! aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws lambda create-function-url-config \
    --function-name "$FUNCTION_NAME" \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["*"],"AllowHeaders":["*"]}' \
    --region "$AWS_REGION" >/dev/null
fi

echo "== Ensuring the Function URL is publicly invocable =="
ADD_URL_PERMISSION_OUTPUT="$(aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE \
  --region "$AWS_REGION" 2>&1)" || {
    if ! echo "$ADD_URL_PERMISSION_OUTPUT" | grep -q "ResourceConflictException"; then
      echo "$ADD_URL_PERMISSION_OUTPUT" >&2
      exit 1
    fi
    echo "(already granted on a prior run)"
  }

FUNCTION_URL="$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'FunctionUrl' --output text)"

echo ""
echo "== IMPORTANT: verify the Function URL is actually reachable before wiring the frontend to it =="
echo "A public (AuthType=NONE) Function URL returned Forbidden the first time this was tried in this"
echo "account, before CloudFront was ever involved -- that specific failure was never conclusively"
echo "root-caused (attention shifted to the CloudFront+OAC case instead). Confirm this works on its"
echo "own first:"
echo ""
echo "  curl -i -X POST ${FUNCTION_URL}api/cur/load -H 'Content-Type: application/json' -d '{}'"
echo ""
echo "Expect a 422 (FastAPI validation error for the empty body) or a real response -- NOT Forbidden."
echo "If it's Forbidden, stop here and report back rather than proceeding to deploy_frontend.sh."
echo ""

cat <<EOF

Backend deployed.

  API endpoint (fast calls, e.g. /api/health):  ${API_ENDPOINT}
  Function URL (slow calls, e.g. /api/cur/load): ${FUNCTION_URL}

  Both require the app-level CUR_DASHBOARD_API_KEY -- see require_api_key
  in main.py. The Function URL exists specifically because API Gateway's
  30-second integration timeout is hard and not configurable, and a real
  CUR export can take far longer than that to download/aggregate; calling
  the Function URL directly (no CloudFront, no API Gateway) has no such
  ceiling -- only the Lambda's own --timeout (900s, its max) applies.
  VERIFY THE FUNCTION URL WORKS (see the curl command printed above)
  before running deploy_frontend.sh -- a plain public Function URL
  returned Forbidden the first time this was tried in this account,
  before CloudFront was ever involved.

Next: run deploy_frontend.sh with LAMBDA_FUNCTION_NAME=$FUNCTION_NAME --
it wires the API endpoint into the CloudFront distribution as the /api/*
origin, and builds the frontend to call the Function URL directly for
/api/cur/load.

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
