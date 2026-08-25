"""Cross-account access via sts:AssumeRole.

The dashboard never stores long-lived credentials: every request assumes the
customer's role fresh using the role ARN + external ID supplied in the
request, and the resulting temporary credentials live only for the duration
of that single request (they are never written to disk or cached between
requests).
"""

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException


def assume_role(role_arn: str, external_id: str, session_name: str, duration_seconds: int = 3600) -> dict:
    sts = boto3.client("sts")
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
