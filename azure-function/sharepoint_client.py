import os
import requests

GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


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
    # site_url format: cloudenablersinc.sharepoint.com/sites/SupportTeam
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


def upload_file(local_path: str, sharepoint_folder: str, filename: str) -> str:
    """Upload a local file to SharePoint. Returns the SharePoint file URL."""
    token = _get_graph_token()
    site_url = os.environ["SHAREPOINT_SITE_URL"]
    site_id = _get_site_id(token, site_url)
    drive_id = _get_drive_id(token, site_id)

    # Ensure folder path starts without leading slash
    folder = sharepoint_folder.lstrip("/")
    upload_url = f"{GRAPH_BASE}/drives/{drive_id}/root:/{folder}/{filename}:/content"

    with open(local_path, "rb") as fh:
        file_bytes = fh.read()

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
    return resp.json().get("webUrl", "")
