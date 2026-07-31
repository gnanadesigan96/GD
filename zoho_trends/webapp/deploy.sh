#!/usr/bin/env bash
# deploy.sh — one-time provisioning + deploy of the Zoho ticket trend dashboard
# to Azure Functions (Linux, Python, Consumption plan).
#
# Run this from YOUR OWN machine (or Azure Cloud Shell) — it needs the Azure
# CLI authenticated against your subscription and network access to
# management.azure.com, neither of which this Claude Code sandbox has.
#
# Prerequisites:
#   - Azure CLI:              https://learn.microsoft.com/cli/azure/install-azure-cli
#   - Azure Functions Core Tools v4: https://learn.microsoft.com/azure/azure-functions/functions-run-local
#   - `az login` already run (or run it now — device-code flow if headless:
#     `az login --use-device-code`)
#
# No Zoho credentials are needed here or ever stored in Azure — the deployed
# app takes them from the browser form on each request (see function_app.py).
set -euo pipefail

# ── Edit these ────────────────────────────────────────────────────────────
RESOURCE_GROUP="rg-corestack-zoho-dashboard"   # reuse rg-corestack-reports if you'd rather not create a new one
LOCATION="eastus"                              # match your other CoreStack Azure resources' region
STORAGE_ACCOUNT="stcorestackzoho$RANDOM"       # storage account names must be globally unique, lowercase, <=24 chars
FUNCTION_APP_NAME="corestack-zoho-trend-dashboard"   # becomes https://$FUNCTION_APP_NAME.azurewebsites.net
# ──────────────────────────────────────────────────────────────────────────

echo "==> Resource group: $RESOURCE_GROUP ($LOCATION)"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

echo "==> Storage account: $STORAGE_ACCOUNT"
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --output none

echo "==> Function app: $FUNCTION_APP_NAME (Python, Linux, Consumption)"
az functionapp create \
  --name "$FUNCTION_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --storage-account "$STORAGE_ACCOUNT" \
  --consumption-plan-location "$LOCATION" \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux \
  --output none

echo "==> Publishing zoho_trends/webapp ..."
cd "$(dirname "$0")"
func azure functionapp publish "$FUNCTION_APP_NAME" --python

echo ""
echo "Done. Dashboard: https://$FUNCTION_APP_NAME.azurewebsites.net/api/dashboard"
echo "(Anonymous auth is enabled on the HTTP routes — see function_app.py's"
echo " AuthLevel.ANONYMOUS. Put this behind your org's SSO / Front Door / IP"
echo " restriction if it shouldn't be publicly reachable — it's a bare"
echo " Function App URL with no auth of its own, just credentials-per-request.)"
