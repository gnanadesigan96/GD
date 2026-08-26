#!/usr/bin/env bash
# Build the backend as a container image, push it to ECR, and create/update
# the Lambda function, an API Gateway HTTP API in front of it, and a
# DynamoDB table used to run slow CUR loads as async jobs.
#
# Why async jobs instead of one request/response: API Gateway's 30-second
# integration timeout is hard and not configurable, and a real customer CUR
# export (151 part files) blew past even Lambda's own 120s timeout -- no
# amount of query optimization changes that ceiling. Two approaches to
# escape it were tried and abandoned before this one: (1) a Function URL
# behind CloudFront + Origin Access Control -- confirmed broken in this
# account by a controlled SigV4-signing test; (2) a *public* Function URL
# called directly, bypassing CloudFront entirely -- also returned Forbidden
# when tested directly with plain curl, ruling it out too (root cause
# unconfirmed; this account rejects unauthenticated Function URL
# invocations by some mechanism broader than what was checked). Since
# neither Function URL path works here, POST /api/cur/load now only
# creates a job record and fires an async (fire-and-forget) self-invocation
# of this same Lambda to do the real work -- see main.py's _dispatch_job
# and lambda_handler.py's routing. That self-invocation isn't a synchronous
# HTTP call through API Gateway or a Function URL at all, so neither's
# timeout applies to it -- only this Lambda's own --timeout does, which is
# why that's set to Lambda's max (900s) below. The frontend polls
# GET /api/cur/job/{job_id} for the result; both that and the initial POST
# are fast enough to stay well within API Gateway's 30s ceiling.
#
# Requires: docker, aws cli v2, credentials with permission to manage ECR,
# Lambda, API Gateway, DynamoDB, and IAM in the target account/region.
#
# Usage: AWS_REGION=us-east-1 ./deploy_backend.sh
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="${FUNCTION_NAME:-cur-dashboard-backend}"
ECR_REPO_NAME="${ECR_REPO_NAME:-cur-dashboard-backend}"
ROLE_NAME="${ROLE_NAME:-cur-dashboard-lambda-role}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
MEMORY_MB="${MEMORY_MB:-10240}"     # Lambda's max -- more memory = more vCPU (up to 6) *and* more RAM for DuckDB to aggregate in without spilling to /tmp. A real (small) test account's one-month ZIP-CUR export alone used 1.4GB RSS decompressing 3 part files, and a larger customer export hit "Out of Memory" spilling past EPHEMERAL_STORAGE_MB's already-maxed 10GB -- once disk is maxed, more RAM is the only remaining lever
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

JOBS_TABLE_NAME="${JOBS_TABLE_NAME:-${FUNCTION_NAME}-jobs}"

echo "== Ensuring the DynamoDB jobs table exists =="
if ! aws dynamodb describe-table --table-name "$JOBS_TABLE_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws dynamodb create-table \
    --table-name "$JOBS_TABLE_NAME" \
    --attribute-definitions AttributeName=job_id,AttributeType=S \
    --key-schema AttributeName=job_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$AWS_REGION" >/dev/null
  aws dynamodb wait table-exists --table-name "$JOBS_TABLE_NAME" --region "$AWS_REGION"
  # TTL means every job record auto-deletes ~30 minutes after it's written
  # (see jobs.py) -- only job status and the same small aggregated result
  # the API already returns is ever stored here, and only briefly.
  aws dynamodb update-time-to-live \
    --table-name "$JOBS_TABLE_NAME" \
    --time-to-live-specification "Enabled=true,AttributeName=ttl" \
    --region "$AWS_REGION" >/dev/null
fi
JOBS_TABLE_ARN="arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/${JOBS_TABLE_NAME}"

echo "== Ensuring the Lambda execution role can use the jobs table and invoke itself =="
JOB_POLICY_DOC=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"],
      "Resource": "${JOBS_TABLE_ARN}"
    },
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "${LAMBDA_ARN}"
    }
  ]
}
EOF
)
aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name CurDashboardJobsAccess --policy-document "$JOB_POLICY_DOC"

echo "== Setting CUR_DASHBOARD_JOBS_TABLE (merged with any existing environment variables) =="
# update-function-configuration replaces the ENTIRE Environment.Variables
# map, not just the keys given -- reading the current map first and merging
# into it avoids wiping out CUR_DASHBOARD_CALLER_*/CUR_DASHBOARD_API_KEY if
# they were already set by hand.
EXISTING_ENV_JSON="$(aws lambda get-function-configuration --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'Environment.Variables' --output json 2>/dev/null || echo 'null')"
MERGED_ENV_JSON="$(echo "$EXISTING_ENV_JSON" | python3 -c "
import json, sys
existing = json.load(sys.stdin) or {}
existing['CUR_DASHBOARD_JOBS_TABLE'] = '${JOBS_TABLE_NAME}'
print(json.dumps({'Variables': existing}))
")"
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --environment "$MERGED_ENV_JSON" \
  --region "$AWS_REGION" >/dev/null
aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$AWS_REGION"

cat <<EOF

Backend deployed.

  API endpoint: ${API_ENDPOINT}
  Jobs table:   ${JOBS_TABLE_NAME}

  Every route requires the app-level CUR_DASHBOARD_API_KEY -- see
  require_api_key in main.py. POST /api/cur/load starts a job and returns
  a job_id immediately; GET /api/cur/job/{job_id} polls for the result.
  The actual work runs as an async self-invocation of this same Lambda,
  outside any HTTP request's timeout -- only this function's own --timeout
  (${TIMEOUT_SECONDS}s) bounds how long a single load can take.

Next: run deploy_frontend.sh with LAMBDA_FUNCTION_NAME=$FUNCTION_NAME --
it wires this API endpoint into the CloudFront distribution as the /api/*
origin.

Set CUR_DASHBOARD_CALLER_ACCESS_KEY_ID / _SECRET_ACCESS_KEY (or Azure Key
Vault) and CUR_DASHBOARD_API_KEY on the function so it can actually assume
customer roles -- see backend/.env.example for the full list. Fetch the
current environment first and merge into it (update-function-configuration
replaces the whole map, so a plain --environment call would wipe out
CUR_DASHBOARD_JOBS_TABLE and anything else already set):

  aws lambda get-function-configuration --function-name "$FUNCTION_NAME" \\
    --region "$AWS_REGION" --query 'Environment.Variables' --output json > /tmp/cur-dashboard-env.json
  # edit /tmp/cur-dashboard-env.json: add CUR_DASHBOARD_CALLER_ACCESS_KEY_ID,
  # CUR_DASHBOARD_CALLER_SECRET_ACCESS_KEY, and CUR_DASHBOARD_API_KEY
  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" \\
    --environment "Variables=\$(cat /tmp/cur-dashboard-env.json)" \\
    --region "$AWS_REGION"

Pass the same CUR_DASHBOARD_API_KEY value as API_KEY to deploy_frontend.sh,
so the frontend's requests are accepted.
EOF
