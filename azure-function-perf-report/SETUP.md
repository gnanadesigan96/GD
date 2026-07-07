# CoreStack Performance Report — Automated with OpenVPN

Automated daily report that establishes an OpenVPN tunnel inside a Docker container,
connects to 7 MongoDB environments, generates HTML + CSV, and uploads to SharePoint.

## Why Docker + ACI instead of Azure Functions?

Azure Functions run in a **sandboxed environment** — you cannot install OpenVPN,
create TUN/TAP devices, or run as root. To use your existing `.ovpn` file, we run
the report inside a Docker container on **Azure Container Instances (ACI)**, which
supports privileged networking. A **Logic App** triggers it on a daily schedule.

## Architecture

```
Logic App Timer (daily 18:30 IST)
    │
    ▼
Azure Container Instance (Docker)
    │
    ├── OpenVPN client ──► VPN tunnel ──► MongoDB hosts
    │                                      4.213.1.249, 52.154.142.32,
    │                                      74.162.91.2, 20.112.121.242,
    │                                      4.180.107.93, 40.76.52.237,
    │                                      20.83.185.233
    │
    └── Microsoft Graph API ──► SharePoint
                                  └── General/Cost-Performance-Report/
                                       ├── corestack-performance-report.html
                                       └── Dump/corestack_section1_raw_*.csv
```

## Files

```
azure-function-perf-report/
├── docker/
│   ├── Dockerfile          # Container image (Python 3.12 + OpenVPN)
│   └── entrypoint.sh       # Starts VPN → runs report → uploads → exits
├── vpn/
│   └── client.ovpn.sample  # Sample OpenVPN config (replace with yours)
├── perf_report.py          # Report generator (MongoDB queries + HTML/CSV)
├── sharepoint_upload.py    # SharePoint upload via Microsoft Graph API
├── run_report.py           # Standalone entry point for Docker
├── requirements.txt        # Python dependencies
└── SETUP.md                # This file
```

---

## Step 1: Prepare Your OpenVPN Config

1. Copy your `.ovpn` file into the `vpn/` directory:
   ```bash
   cp /path/to/your-vpn-config.ovpn vpn/client.ovpn
   ```

2. If your `.ovpn` file references external certificate files (`ca`, `cert`, `key`),
   you have two options:

   **Option A** — Inline them (recommended):
   Edit `client.ovpn` and replace file references with inline blocks:
   ```
   # Remove these lines:
   #   ca   ca.crt
   #   cert client.crt
   #   key  client.key

   # Add inline blocks instead:
   <ca>
   -----BEGIN CERTIFICATE-----
   (paste contents of ca.crt)
   -----END CERTIFICATE-----
   </ca>

   <cert>
   -----BEGIN CERTIFICATE-----
   (paste contents of client.crt)
   -----END CERTIFICATE-----
   </cert>

   <key>
   -----BEGIN PRIVATE KEY-----
   (paste contents of client.key)
   -----END PRIVATE KEY-----
   </key>
   ```

   **Option B** — Keep separate files and mount them all (shown in Step 4).

3. Verify your `.ovpn` works locally:
   ```bash
   sudo openvpn --config vpn/client.ovpn
   ```

---

## Step 2: Register Azure AD App for SharePoint

1. Go to **Azure Portal → Microsoft Entra ID → App registrations → New registration**
2. Name: `CoreStack-Report-Uploader`
3. Under **API permissions**, add:
   - Microsoft Graph → Application → `Sites.ReadWrite.All`
4. Click **Grant admin consent**
5. Under **Certificates & secrets** → **Client secrets** → New client secret
6. Note down:
   - **Directory (tenant) ID**
   - **Application (client) ID**
   - **Client secret value**

---

## Step 3: Build & Push the Docker Image

```bash
# Create Azure Container Registry (one-time)
az group create --name rg-corestack-reports --location eastus

az acr create \
  --resource-group rg-corestack-reports \
  --name acrcorestack \
  --sku Basic \
  --admin-enabled true

# Login to ACR
az acr login --name acrcorestack

# Build and push (run from azure-function-perf-report/ directory)
docker build -t acrcorestack.azurecr.io/perf-report:latest -f docker/Dockerfile .
docker push acrcorestack.azurecr.io/perf-report:latest
```

---

## Step 4: Store the VPN Config in Azure

Store your `.ovpn` file as an **Azure Key Vault secret** or **Azure File Share**
so the container can mount it at runtime (never bake credentials into the image).

### Using Azure File Share (simpler):

```bash
# Create storage account
az storage account create \
  --name stcorestackvpn \
  --resource-group rg-corestack-reports \
  --sku Standard_LRS

# Create file share
az storage share-rm create \
  --storage-account stcorestackvpn \
  --name vpn-config \
  --quota 1

# Upload your .ovpn file
az storage file upload \
  --account-name stcorestackvpn \
  --share-name vpn-config \
  --source vpn/client.ovpn \
  --path client.ovpn

# Get storage account key (needed for ACI mount)
az storage account keys list \
  --resource-group rg-corestack-reports \
  --account-name stcorestackvpn \
  --query "[0].value" -o tsv
```

---

## Step 5: Create the Azure Container Instance

```bash
# Get ACR credentials
ACR_SERVER="acrcorestack.azurecr.io"
ACR_USER=$(az acr credential show --name acrcorestack --query "username" -o tsv)
ACR_PASS=$(az acr credential show --name acrcorestack --query "passwords[0].value" -o tsv)
STORAGE_KEY=$(az storage account keys list --account-name stcorestackvpn --query "[0].value" -o tsv)

az container create \
  --resource-group rg-corestack-reports \
  --name aci-perf-report \
  --image acrcorestack.azurecr.io/perf-report:latest \
  --registry-login-server "$ACR_SERVER" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --os-type Linux \
  --cpu 1 \
  --memory 1.5 \
  --restart-policy Never \
  --environment-variables \
    SHAREPOINT_TENANT_ID="<your-tenant-id>" \
    SHAREPOINT_CLIENT_ID="<your-app-client-id>" \
    SHAREPOINT_SITE_URL="cloudenablersinc.sharepoint.com/sites/SupportTeam" \
    SHAREPOINT_REPORT_FOLDER="General/Cost-Performance-Report" \
    SHAREPOINT_CSV_FOLDER="General/Cost-Performance-Report/Dump" \
  --secure-environment-variables \
    SHAREPOINT_CLIENT_SECRET="<your-app-client-secret>" \
  --azure-file-volume-account-name stcorestackvpn \
  --azure-file-volume-account-key "$STORAGE_KEY" \
  --azure-file-volume-share-name vpn-config \
  --azure-file-volume-mount-path /etc/openvpn
```

### Test it manually:

```bash
# Start the container
az container start \
  --resource-group rg-corestack-reports \
  --name aci-perf-report

# Watch logs
az container logs \
  --resource-group rg-corestack-reports \
  --name aci-perf-report \
  --follow

# Check status
az container show \
  --resource-group rg-corestack-reports \
  --name aci-perf-report \
  --query "containers[0].instanceView.currentState"
```

---

## Step 6: Schedule with Logic App (Daily 18:30 IST)

### Via Azure Portal:

1. **Create a Logic App** (Consumption plan):
   - Name: `logic-perf-report-schedule`
   - Resource group: `rg-corestack-reports`

2. **Designer** → Add trigger:
   - **Recurrence** trigger
   - Interval: `1 Day`
   - At these hours: `13` (UTC = 18:30 IST)
   - At these minutes: `0`
   - Time zone: `UTC`

3. **Add action** → Search "Azure Container Instances":
   - Action: **Start containers in a container group**
   - Subscription: (your subscription)
   - Resource Group: `rg-corestack-reports`
   - Container Group: `aci-perf-report`

4. **Save** the Logic App.

### Via Azure CLI:

```bash
# Create the Logic App definition
cat > /tmp/logic-app-definition.json << 'JSONEOF'
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "triggers": {
      "daily_1830_ist": {
        "type": "Recurrence",
        "recurrence": {
          "frequency": "Day",
          "interval": 1,
          "schedule": {
            "hours": ["13"],
            "minutes": ["0"]
          },
          "timeZone": "UTC"
        }
      }
    },
    "actions": {
      "Start_Container": {
        "type": "ApiConnection",
        "inputs": {
          "host": {
            "connection": {
              "name": "@parameters('$connections')['aci']['connectionId']"
            }
          },
          "method": "post",
          "path": "/subscriptions/@{encodeURIComponent('<SUB_ID>')}/resourceGroups/@{encodeURIComponent('rg-corestack-reports')}/providers/Microsoft.ContainerInstance/containerGroups/@{encodeURIComponent('aci-perf-report')}/start",
          "queries": {
            "x-ms-api-version": "2019-12-01"
          }
        }
      }
    }
  }
}
JSONEOF

az logic workflow create \
  --resource-group rg-corestack-reports \
  --name logic-perf-report-schedule \
  --definition @/tmp/logic-app-definition.json
```

---

## Step-by-Step Summary

| Step | What                              | One-time? |
|------|-----------------------------------|-----------|
| 1    | Prepare `.ovpn` file              | Yes       |
| 2    | Register Azure AD app (SharePoint)| Yes       |
| 3    | Build & push Docker image to ACR  | On change |
| 4    | Upload `.ovpn` to Azure File Share| Yes       |
| 5    | Create ACI container group        | Yes       |
| 6    | Create Logic App schedule         | Yes       |

---

## Changing the Schedule

Edit the Logic App recurrence trigger in the Azure Portal, or update the hours/minutes
in the CLI definition. The schedule is in **UTC**:

| Desired IST | Set UTC Hours |
|-------------|---------------|
| 06:30 AM    | 1             |
| 12:00 PM    | 6, minute 30  |
| 06:30 PM    | 13            |
| 09:00 PM    | 15, minute 30 |

---

## Updating the Report Script

When you change the report logic:

```bash
# Rebuild and push
docker build -t acrcorestack.azurecr.io/perf-report:latest -f docker/Dockerfile .
docker push acrcorestack.azurecr.io/perf-report:latest

# Restart container to pick up new image
az container restart \
  --resource-group rg-corestack-reports \
  --name aci-perf-report
```

---

## Troubleshooting

**VPN not connecting:**
```bash
# Check OpenVPN logs inside the container
az container exec \
  --resource-group rg-corestack-reports \
  --name aci-perf-report \
  --exec-command "cat /var/log/openvpn.log"
```

**MongoDB timeouts after VPN connects:** Check that your VPN pushes the correct
routes for the MongoDB IPs. Add `route` directives to your `.ovpn` if needed:
```
route 4.213.1.249 255.255.255.255
route 52.154.142.32 255.255.255.255
route 74.162.91.2 255.255.255.255
route 20.112.121.242 255.255.255.255
route 4.180.107.93 255.255.255.255
route 40.76.52.237 255.255.255.255
route 20.83.185.233 255.255.255.255
```

**SharePoint 403:** Ensure Azure AD app has `Sites.ReadWrite.All` (Application type,
not Delegated) with admin consent granted.

**Container keeps restarting:** The `--restart-policy Never` flag prevents this.
The container runs once and stops. The Logic App starts it fresh each day.

**Testing locally:**
```bash
# Build locally
docker build -t perf-report:local -f docker/Dockerfile .

# Run with your real VPN file and env vars
docker run --rm --cap-add=NET_ADMIN --device=/dev/net/tun \
  -v $(pwd)/vpn/client.ovpn:/etc/openvpn/client.ovpn:ro \
  -e SHAREPOINT_TENANT_ID="..." \
  -e SHAREPOINT_CLIENT_ID="..." \
  -e SHAREPOINT_CLIENT_SECRET="..." \
  -e SHAREPOINT_SITE_URL="cloudenablersinc.sharepoint.com/sites/SupportTeam" \
  perf-report:local
```
Note: `--cap-add=NET_ADMIN` and `--device=/dev/net/tun` are required for OpenVPN.
