"""Resolve the size of each CUR part file for display in the UI.

Part files for one billing period almost always live in the same S3
"folder" (the manifest just lists them by key, not size), so this groups
part_keys by parent prefix and does one paginated list_objects_v2 call per
distinct prefix -- usually exactly one -- rather than a HeadObject per part
file, which would be hundreds of extra round trips for a real export.
"""

import posixpath

from botocore.exceptions import ClientError
from fastapi import HTTPException


def list_part_file_sizes(s3_client, bucket: str, part_keys: list[str]) -> dict[str, int]:
    wanted = set(part_keys)
    sizes: dict[str, int] = {}
    prefixes = {posixpath.dirname(k) for k in part_keys}
    paginator = s3_client.get_paginator("list_objects_v2")
    try:
        for prefix in prefixes:
            list_prefix = f"{prefix}/" if prefix else ""
            for page in paginator.paginate(Bucket=bucket, Prefix=list_prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key in wanted:
                        sizes[key] = obj["Size"]
    except ClientError as exc:
        raise HTTPException(status_code=502, detail=f"Unable to list report part files: {exc}") from exc
    return sizes
