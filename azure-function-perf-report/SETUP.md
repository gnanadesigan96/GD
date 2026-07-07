# Azure Function — CoreStack Performance Report

Automated daily report that connects to 7 MongoDB environments, generates an HTML
performance report + CSV raw data dump, and uploads both to SharePoint.

## Architecture

```
Timer Trigger (daily 18:30 IST)
    │
    ▼
Azure Function (Python 3.12)
    │
    ├── VNet Integration ──► MongoDB hosts (private IPs)
    │                         4.213.1.249, 52.154.142.32, 74.162.91.2,
    │                         20.112.121.242, 4.180.107.93, 40.76.52.237,
    │                         20.83.185.233
    │
    └── Microsoft Graph API ──► SharePoint
                                  └── General/Cost-Performance-Report/
                                       ├── corestack-performance-report.html
                                       └── Dump/corestack_section1_raw_*.csv
```

## Prerequisites

1. **Azure Subscription** with permissions to create:
   - Function App
   - Virtual Network + Subnets
   - VPN Gateway or VNet peering (to reach MongoDB hosts)

2. **Azure AD App Registration** for SharePoint access:
   - API Permissions: `Sites.ReadWrite.All` (Application)
   - Grant admin consent

3. **Network connectivity** to all 7 MongoDB hosts (ports 27017 / 1200)

---

## Step 1: Create the VNet & VPN Gateway

Your MongoDB hosts are on private/public IPs that currently require VPN.
You need an Azure VNet that can route to them.

### Option A: VNet Peering (if MongoDB VMs are in Azure)

If the MongoDB hosts are Azure VMs in another VNet:

```bash
# Create Function App VNet
az network vnet create \
  --resource-group rg-corestack-reports \
  --name vnet-perf-report \
  --address-prefix 10.100.0.0/16 \
  --subnet-name snet-functions \
  --subnet-prefix 10.100.1.0/24

# Peer with the MongoDB VNet (both directions)
az network vnet peering create \
  --resource-group rg-corestack-reports \
  --name peer-to-mongo \
  --vnet-name vnet-perf-report \
  --remote-vnet /subscriptions/<SUB_ID>/resourceGroups/<MONGO_RG>/providers/Microsoft.Network/virtualNetworks/<MONGO_VNET> \
  --allow-vnet-access

# Repeat in reverse from the MongoDB VNet side
```

### Option B: Point-to-Site VPN (if MongoDB hosts are on-prem / other cloud)

```bash
# Create VNet
az network vnet create \
  --resource-group rg-corestack-reports \
  --name vnet-perf-report \
  --address-prefix 10.100.0.0/16

# Create GatewaySubnet (required name)
az network vnet subnet create \
  --resource-group rg-corestack-reports \
  --vnet-name vnet-perf-report \
  --name GatewaySubnet \
  --address-prefix 10.100.0.0/27

# Create function subnet (delegated to Microsoft.Web)
az network vnet subnet create \
  --resource-group rg-corestack-reports \
  --vnet-name vnet-perf-report \
  --name snet-functions \
  --address-prefix 10.100.1.0/24 \
  --delegations Microsoft.Web/serverFarms

# Create VPN Gateway (takes ~30 min)
az network public-ip create \
  --resource-group rg-corestack-reports \
  --name pip-vpngw \
  --sku Standard

az network vnet-gateway create \
  --resource-group rg-corestack-reports \
  --name vpngw-perf-report \
  --vnet vnet-perf-report \
  --gateway-type Vpn \
  --vpn-type RouteBased \
  --sku VpnGw1 \
  --public-ip-address pip-vpngw

# Add routes for MongoDB hosts
az network vnet-gateway update \
  --resource-group rg-corestack-reports \
  --name vpngw-perf-report \
  --set "bgpSettings=null"

# Configure Site-to-Site connection to your on-prem VPN appliance
az network vpn-connection create \
  --resource-group rg-corestack-reports \
  --name conn-to-onprem \
  --vnet-gateway1 vpngw-perf-report \
  --local-gateway2 <YOUR_LOCAL_GATEWAY> \
  --shared-key <YOUR_PSK>
```

---

## Step 2: Create the Function App

```bash
# Create resource group
az group create --name rg-corestack-reports --location eastus

# Create storage account (required by Functions)
az storage account create \
  --name stcorestackreports \
  --resource-group rg-corestack-reports \
  --sku Standard_LRS

# Create Function App (Python 3.12, Consumption or Premium)
# NOTE: Premium (EP1) is recommended for VNet integration
az functionapp create \
  --resource-group rg-corestack-reports \
  --name func-corestack-perf-report \
  --storage-account stcorestackreports \
  --runtime python \
  --runtime-version 3.12 \
  --functions-version 4 \
  --os-type Linux \
  --plan-name plan-perf-report \
  --sku EP1

# Enable VNet integration
az functionapp vnet-integration add \
  --resource-group rg-corestack-reports \
  --name func-corestack-perf-report \
  --vnet vnet-perf-report \
  --subnet snet-functions

# Route all outbound traffic through VNet
az functionapp config appsettings set \
  --resource-group rg-corestack-reports \
  --name func-corestack-perf-report \
  --settings WEBSITE_VNET_ROUTE_ALL=1
```

---

## Step 3: Configure App Settings

```bash
az functionapp config appsettings set \
  --resource-group rg-corestack-reports \
  --name func-corestack-perf-report \
  --settings \
    SHAREPOINT_TENANT_ID="<your-tenant-id>" \
    SHAREPOINT_CLIENT_ID="<your-app-client-id>" \
    SHAREPOINT_CLIENT_SECRET="<your-app-client-secret>" \
    SHAREPOINT_SITE_URL="cloudenablersinc.sharepoint.com/sites/SupportTeam" \
    SHAREPOINT_REPORT_FOLDER="General/Cost-Performance-Report" \
    SHAREPOINT_CSV_FOLDER="General/Cost-Performance-Report/Dump"
```

---

## Step 4: Register Azure AD App for SharePoint

1. Go to **Azure Portal → Azure Active Directory → App registrations → New registration**
2. Name: `CoreStack-SharePoint-Uploader`
3. Under **API permissions**, add:
   - Microsoft Graph → Application → `Sites.ReadWrite.All`
4. Click **Grant admin consent**
5. Under **Certificates & secrets**, create a client secret
6. Copy the **Application (client) ID** and **Secret** into the Function App settings

---

## Step 5: Deploy

```bash
# From the azure-function-perf-report/ directory:
func azure functionapp publish func-corestack-perf-report
```

Or use VS Code with the Azure Functions extension:
1. Open `azure-function-perf-report/` folder
2. Azure icon → Functions → Deploy to Function App

---

## Step 6: Verify

```bash
# Check function is registered
az functionapp function list \
  --resource-group rg-corestack-reports \
  --name func-corestack-perf-report

# Trigger manually for testing
az functionapp function invoke \
  --resource-group rg-corestack-reports \
  --name func-corestack-perf-report \
  --function-name perf_report_trigger

# Check logs
az functionapp log tail \
  --resource-group rg-corestack-reports \
  --name func-corestack-perf-report
```

---

## Schedule

| UTC         | IST          | Description              |
|-------------|--------------|--------------------------|
| 13:00 daily | 18:30 daily  | Timer fires              |

To change the schedule, update the cron expression in `function_app.py`:
```python
schedule="0 0 13 * * *"   # second minute hour day month weekday
```

---

## Files

| File                  | Purpose                                        |
|-----------------------|------------------------------------------------|
| `function_app.py`     | Azure Function entry point (timer trigger)     |
| `perf_report.py`      | Report generator (MongoDB queries + HTML/CSV)  |
| `sharepoint_upload.py`| SharePoint upload via Microsoft Graph API      |
| `host.json`           | Azure Functions host configuration             |
| `requirements.txt`    | Python dependencies                            |
| `local.settings.json.template` | Template for local dev settings       |

---

## Troubleshooting

**MongoDB connection timeouts**: Verify VNet integration is active and NSG rules
allow outbound to MongoDB IPs on ports 27017/1200.

**SharePoint 403**: Ensure the Azure AD app has `Sites.ReadWrite.All` with admin
consent granted, and the site URL matches exactly.

**Function timeout**: The `host.json` sets `functionTimeout` to 10 minutes.
If the report takes longer, increase it or switch to a Durable Function.

**Testing locally with VPN**: Connect to your VPN first, then:
```bash
cp local.settings.json.template local.settings.json
# Fill in the real values
func start
```
