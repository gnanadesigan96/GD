"""Fetch the AWS caller identity's access key / secret key from Azure Key Vault.

This keeps the actual key material out of env vars, .env files, and this
repo entirely -- it's read from the vault at runtime instead.

KEY_VAULT_URL and the two secret names below are placeholders. Replace them
once the vault is provisioned (or set the equivalent env vars, which take
priority over the placeholders). Authentication uses DefaultAzureCredential,
which picks up whatever's available in the environment it runs in: Managed
Identity on Azure, an `az login` session locally, or a service principal via
AZURE_CLIENT_ID / AZURE_CLIENT_SECRET / AZURE_TENANT_ID env vars.

If KEY_VAULT_URL is left as the placeholder, the vault is treated as "not
configured" and aws_client.py falls back to CUR_DASHBOARD_CALLER_* env vars
or boto3's default credential chain -- so this is safe to leave unfilled
during local development.
"""

import os
from functools import lru_cache

# TODO: replace with the real vault URL and secret names, or set
# AZURE_KEY_VAULT_URL / AZURE_KV_ACCESS_KEY_SECRET_NAME /
# AZURE_KV_SECRET_KEY_SECRET_NAME instead.
KEY_VAULT_URL = os.environ.get("AZURE_KEY_VAULT_URL", "https://<your-vault-name>.vault.azure.net/")
ACCESS_KEY_SECRET_NAME = os.environ.get("AZURE_KV_ACCESS_KEY_SECRET_NAME", "cur-dashboard-caller-access-key-id")
SECRET_KEY_SECRET_NAME = os.environ.get("AZURE_KV_SECRET_KEY_SECRET_NAME", "cur-dashboard-caller-secret-access-key")


def _is_configured() -> bool:
    return "<" not in KEY_VAULT_URL


@lru_cache(maxsize=1)
def load_caller_credentials() -> tuple[str, str] | None:
    """Returns (access_key_id, secret_access_key) from Key Vault, or None if no vault is configured.

    Cached for the life of the process -- if the secrets are rotated in the
    vault, the backend needs a restart to pick up the new values.
    """
    if not _is_configured():
        return None

    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    client = SecretClient(vault_url=KEY_VAULT_URL, credential=DefaultAzureCredential())
    access_key = client.get_secret(ACCESS_KEY_SECRET_NAME).value
    secret_key = client.get_secret(SECRET_KEY_SECRET_NAME).value
    return access_key, secret_key
