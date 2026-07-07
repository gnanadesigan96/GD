"""
sharepoint_upload.py
Upload files to SharePoint via Microsoft Graph API (client_credentials flow).
Supports large files (>4 MB) using upload sessions.
"""
import logging
import os

import requests

GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
LARGE_FILE_THRESHOLD = 4 * 1024 * 1024  # 4 MB


def _get_graph_token() -> str:
    tenant_id = os.environ["SHAREPOINT_TENANT_ID"]
    url = GRAPH_TOKEN_URL.format(tenant_id=tenant_id)
    resp = requests.post(url, data={
        "client_id":     os.environ["SHAREPOINT_CLIENT_ID"],
        "client_secret": os.environ["SHAREPOINT_CLIENT_SECRET"],
        "scope":         "https://graph.microsoft.com/.default",
        "grant_type":    "client_credentials",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_site_id(token: str, site_url: str) -> str:
    parts = site_url.replace("https://", "").split("/sites/")
    hostname = parts[0]
    site_name = parts[1] if len(parts) > 1 else ""
    resp = requests.get(
        f"{GRAPH_BASE}/sites/{hostname}:/sites/{site_name}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _get_drive_id(token: str, site_id: str) -> str:
    resp = requests.get(
        f"{GRAPH_BASE}/sites/{site_id}/drive",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def upload_bytes(file_bytes: bytes, folder: str, filename: str) -> str:
    """Upload bytes to SharePoint. Returns the SharePoint file URL."""
    token = _get_graph_token()
    site_url = os.environ["SHAREPOINT_SITE_URL"]
    site_id = _get_site_id(token, site_url)
    drive_id = _get_drive_id(token, site_id)
    folder = folder.lstrip("/")

    if len(file_bytes) > LARGE_FILE_THRESHOLD:
        return _upload_large(token, drive_id, folder, filename, file_bytes)

    upload_url = f"{GRAPH_BASE}/drives/{drive_id}/root:/{folder}/{filename}:/content"
    resp = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        },
        data=file_bytes,
        timeout=120,
    )
    resp.raise_for_status()
    web_url = resp.json().get("webUrl", "")
    logging.info("Uploaded %s (%d bytes) -> %s", filename, len(file_bytes), web_url)
    return web_url


def _upload_large(token: str, drive_id: str, folder: str, filename: str,
                  file_bytes: bytes) -> str:
    session_url = (
        f"{GRAPH_BASE}/drives/{drive_id}/root:/{folder}/{filename}"
        f":/createUploadSession"
    )
    resp = requests.post(
        session_url,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
        timeout=30,
    )
    resp.raise_for_status()
    upload_url = resp.json()["uploadUrl"]

    chunk_size = 10 * 1024 * 1024  # 10 MB chunks
    total = len(file_bytes)
    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)
        chunk = file_bytes[start:end]
        headers = {
            "Content-Length": str(len(chunk)),
            "Content-Range": f"bytes {start}-{end - 1}/{total}",
        }
        resp = requests.put(upload_url, headers=headers, data=chunk, timeout=120)
        resp.raise_for_status()

    return resp.json().get("webUrl", "")
