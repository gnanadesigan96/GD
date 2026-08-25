"""Cross-account access via sts:AssumeRole.

The dashboard never stores long-lived credentials for *customers*: every
request assumes the customer's role fresh using the role ARN + external ID
supplied in the request, and the resulting temporary credentials live only
for the duration of that single request (they are never written to disk or
cached between requests).

sts:AssumeRole itself has to be called *as somebody* -- an IAM identity that
the customer's role trust policy names as a trusted principal. That caller
identity's own access key / secret key come from, in priority order:

  1. Azure Key Vault (see secrets.py), if a vault is configured there
  2. CUR_DASHBOARD_CALLER_ACCESS_KEY_ID / CUR_DASHBOARD_CALLER_SECRET_ACCESS_KEY
     env vars
  3. boto3's default credential provider chain (e.g. an instance/task role),
     which is preferable to static keys in any environment where it's
     available

so the key material itself never has to live in code or a committed file.
"""

import os

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException

from .secrets import load_caller_credentials

_STS_REGION = os.environ.get("CUR_DASHBOARD_STS_REGION", "us-east-1")


def _sts_client():
    vault_creds = load_caller_credentials()
    if vault_creds:
        access_key, secret_key = vault_creds
    else:
        access_key = os.environ.get("CUR_DASHBOARD_CALLER_ACCESS_KEY_ID")
        secret_key = os.environ.get("CUR_DASHBOARD_CALLER_SECRET_ACCESS_KEY")

    if access_key and secret_key:
        return boto3.client(
            "sts",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=_STS_REGION,
        )
    return boto3.client("sts", region_name=_STS_REGION)


def assume_role(role_arn: str, external_id: str, session_name: str, duration_seconds: int = 3600) -> dict:
    sts = _sts_client()
    try:
        resp = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName=session_name,
            ExternalId=external_id,
            DurationSeconds=duration_seconds,
        )
    except ClientError as exc:
        raise HTTPException(status_code=403, detail=f"Unable to assume role: {exc}") from exc

    creds = resp["Credentials"]
    return {
        "aws_access_key_id": creds["AccessKeyId"],
        "aws_secret_access_key": creds["SecretAccessKey"],
        "aws_session_token": creds["SessionToken"],
    }


def s3_client_for(creds: dict, region: str | None = None):
    return boto3.client("s3", region_name=region, **creds)


def resolve_bucket_region(s3_client, bucket: str, fallback: str = "us-east-1") -> str:
    try:
        location = s3_client.get_bucket_location(Bucket=bucket).get("LocationConstraint")
    except ClientError:
        return fallback
    # AWS returns None/"" for us-east-1, and "EU" for legacy eu-west-1 buckets.
    if not location:
        return fallback
    if location == "EU":
        return "eu-west-1"
    return location
