# Deployment Guide — AKS (Azure Kubernetes Service)

## Architecture on your cluster

```
Internet
   │
   ▼
AKS Ingress (nginx)
   │  replay.your-domain.com
   ▼
[Viewer Pod]  ──────────────────────────────────────────────────────
  nginx container                                                    │
  - Serves the React SPA on /                                        │  ClusterIP
  - Proxies /sessions → session-replay-backend:3001                  │
                                                                     ▼
                                                          [Backend Pod]
                                                            Node.js API
                                                               │
                                                               ▼
                                                     Azure Blob Storage
                                                      (session events)

Your App (web/app servers) ──── POST /sessions → Ingress or direct to Backend
```

The SDK snippet goes in **your existing app** (web server or app server).
It sends data directly to the backend API URL.

---

## Prerequisites

Make sure these are available on the machine where you run `kubectl`:

- `kubectl` connected to your AKS cluster (`az aks get-credentials ...`)
- `docker` + `az acr login YOUR_ACR.azurecr.io`
- `helm` (for ingress controller)
- An **Azure Storage Account** with a container named `session-replay`

---

## Step 1 — Azure Blob Storage

In Azure Portal (or CLI):

```bash
# Create storage account (skip if you have one)
az storage account create \
  --name yourstorageaccount \
  --resource-group your-rg \
  --sku Standard_LRS \
  --location eastus

# Create the container
az storage container create \
  --name session-replay \
  --account-name yourstorageaccount

# Get the connection string (you'll need this in Step 3)
az storage account show-connection-string \
  --name yourstorageaccount \
  --resource-group your-rg \
  --query connectionString -o tsv
```

---

## Step 2 — Build and push Docker images to ACR

Replace `YOUR_ACR` with your Azure Container Registry name throughout.

```bash
# Log in to ACR
az acr login --name YOUR_ACR

# Build and push backend
cd session-replay/backend
docker build -t YOUR_ACR.azurecr.io/session-replay-backend:latest .
docker push YOUR_ACR.azurecr.io/session-replay-backend:latest

# Build and push viewer
cd ../viewer
docker build -t YOUR_ACR.azurecr.io/session-replay-viewer:latest .
docker push YOUR_ACR.azurecr.io/session-replay-viewer:latest
```

---

## Step 3 — Create the namespace and secret

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create the Azure Storage secret (replace with your actual connection string)
kubectl create secret generic session-replay-azure \
  --namespace session-replay \
  --from-literal=connection-string="DefaultEndpointsProtocol=https;AccountName=yourstorageaccount;AccountKey=YOUR_KEY;EndpointSuffix=core.windows.net" \
  --from-literal=container="session-replay"
```

> **Preferred alternative — AKS Workload Identity (no secrets stored in K8s)**
> If your AKS cluster has Workload Identity enabled:
> ```bash
> az aks update --resource-group your-rg --name your-aks --enable-workload-identity
> # Then assign the Storage Blob Data Contributor role to the managed identity
> # and annotate the pod's ServiceAccount — see Azure docs for full steps.
> ```
> Then leave `AZURE_STORAGE_CONNECTION_STRING` out of the backend env and it
> will auto-authenticate via `DefaultAzureCredential`.

---

## Step 4 — Edit the K8s manifests

Open `k8s/backend.yaml` and `k8s/ingress.yaml` and replace these placeholders:

| Placeholder | Replace with |
|---|---|
| `YOUR_ACR.azurecr.io` | Your actual ACR hostname |
| `YOUR_VIEWER_DOMAIN` | Domain or IP where the viewer will be accessed |
| `replay.YOUR_DOMAIN.com` | The hostname you'll use for the viewer |

---

## Step 5 — Deploy to AKS

```bash
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/viewer.yaml
kubectl apply -f k8s/ingress.yaml
```

Verify everything is running:
```bash
kubectl get pods -n session-replay
kubectl get svc  -n session-replay
kubectl get ingress -n session-replay
```

Expected output:
```
NAME                                READY   STATUS    RESTARTS
session-replay-backend-xxxx-yyyy    1/1     Running   0
session-replay-backend-xxxx-zzzz    1/1     Running   0
session-replay-viewer-xxxx-yyyy     1/1     Running   0
session-replay-viewer-xxxx-zzzz     1/1     Running   0
```

---

## Step 6 — Embed the SDK in your application

This is the only change needed on your **web server / app server**.
Add these two lines just before `</body>` in your app's HTML:

```html
<!-- Session Replay SDK -->
<script src="https://replay.YOUR_DOMAIN.com/sdk.min.js"></script>
<script>
  SessionReplay.init({
    endpoint: 'https://replay.YOUR_DOMAIN.com',
    userId: '{{ current_user.id }}',   // inject logged-in user ID from your backend
    maskInputs: true,
  });
</script>
```

> **If your app uses a bundler (React/Vue/Angular):**
> ```js
> // In your root component or login handler
> import { init, identify } from '@session-replay/sdk';
>
> // Call once when app loads
> init({ endpoint: 'https://replay.YOUR_DOMAIN.com', maskInputs: true });
>
> // Call after login to tag the session with the user
> identify(user.id, { email: user.email, role: user.role });
> ```

### Where exactly does this go across your servers?

| Your server | What to do |
|---|---|
| **Web server (Nginx/Apache)** | Add the two `<script>` lines to the HTML template it serves |
| **App server (Node/Python/Java)** | Add to the base HTML layout / template file |
| **Auth server** | Nothing needed — SDK auto-detects login events via network capture |
| **Multiple apps** | Add to each app's HTML that customers use |

---

## Step 7 — Access the viewer

Open `https://replay.YOUR_DOMAIN.com` in your browser.
You will see a list of recorded sessions. Click any session to replay it.

---

## Updating the deployment

When you push new code:

```bash
# Rebuild and push images
docker build -t YOUR_ACR.azurecr.io/session-replay-backend:v1.1 ./backend
docker push YOUR_ACR.azurecr.io/session-replay-backend:v1.1

# Rolling update (zero downtime)
kubectl set image deployment/session-replay-backend \
  backend=YOUR_ACR.azurecr.io/session-replay-backend:v1.1 \
  -n session-replay
```

---

## Troubleshooting

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n session-replay
kubectl logs <pod-name> -n session-replay
```

**SDK not sending data:**
- Open browser DevTools → Network tab → filter by `/sessions`
- You should see `POST /sessions` on page load and `POST /sessions/xxx/events` every 5 seconds

**Blob Storage errors:**
```bash
# Check backend logs
kubectl logs -l app=session-replay-backend -n session-replay
```
Look for `AZURE_STORAGE_CONNECTION_STRING` missing or `AuthorizationFailure`.

**CORS errors in browser:**
- Ensure `CORS_ORIGIN` in `backend.yaml` matches the exact origin of your app
  (e.g. `https://app.yourcompany.com`)
