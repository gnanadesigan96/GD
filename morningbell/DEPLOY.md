# MorningBell — VM Deployment Guide

## What you need
- A VM with Ubuntu 22.04 LTS (DigitalOcean, AWS EC2, Azure, or Hetzner)
- Minimum: 2 vCPU, 2GB RAM, 20GB disk
- A domain name pointed to your VM's IP

---

## Step 1 — Provision a VM

### Recommended: Hetzner (cheapest, EU-based)
1. Go to hetzner.com/cloud
2. Create project → Add server
3. Ubuntu 22.04, CX21 (2 vCPU, 4GB RAM) = €5.77/month
4. Add your SSH key
5. Note the IP address

### Point your domain
Add an A record: `morningbell.yourdomain.com → <VM IP>`

---

## Step 2 — Initial VM Setup

SSH into your VM:
```bash
ssh root@<YOUR_VM_IP>
```

Run the setup script (installs Node.js, PostgreSQL, Nginx, PM2):
```bash
curl -fsSL https://raw.githubusercontent.com/gnanadesigan96/GD/claude/sweet-planck-2o0zu0/morningbell/scripts/setup-vm.sh | bash
```

**Save the database password** shown at the end — you'll need it in Step 3.

---

## Step 3 — Configure Environment

```bash
cd /home/morningbell/morningbell
cp .env.example .env
nano .env
```

Fill in these values at minimum:

```env
# From Step 2 output:
DATABASE_URL=postgresql://morningbell:YOUR_DB_PASSWORD@localhost:5432/morningbell_db

# Generate a random 32+ char string:
NEXTAUTH_SECRET=run_this: openssl rand -base64 32
NEXTAUTH_URL=https://morningbell.yourdomain.com

# Stripe (get from stripe.com → Developers → API keys)
STRIPE_SECRET_KEY=sk_live_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_COMPANION=price_...
STRIPE_PRICE_CARETAKER=price_...
STRIPE_PRICE_PREMIUM=price_...

# Agora (get from console.agora.io)
AGORA_APP_ID=...
AGORA_APP_CERTIFICATE=...
NEXT_PUBLIC_AGORA_APP_ID=...

# Onfido (get from onfido.com → API)
ONFIDO_API_KEY=...

# Twilio (get from twilio.com → Console)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

---

## Step 4 — Deploy the App

```bash
bash /home/morningbell/morningbell/scripts/deploy.sh
```

This will:
- Install all npm dependencies
- Generate Prisma client
- Run database migrations
- Build Next.js
- Start the app with PM2 on port 3000

---

## Step 5 — Setup Nginx + SSL

```bash
bash /home/morningbell/morningbell/scripts/setup-ssl.sh morningbell.yourdomain.com your@email.com
```

Your app is now live at `https://morningbell.yourdomain.com`

---

## Step 6 — Create Admin User

```bash
cd /home/morningbell/morningbell
node scripts/create-admin.js
```

Or directly via psql:
```sql
-- SSH into VM, then:
sudo -u postgres psql morningbell_db

-- Get admin user ID after registering normally, then:
UPDATE "User" SET role = 'ADMIN' WHERE email = 'your@email.com';
```

---

## Step 7 — Setup Daily Backups

```bash
crontab -e
# Add this line:
0 2 * * * /home/morningbell/morningbell/scripts/db-backup.sh >> /home/morningbell/logs/backup.log 2>&1
```

---

## Useful Commands

```bash
# App status
pm2 status

# View live logs
pm2 logs morningbell

# Restart app
pm2 restart morningbell

# Redeploy after code changes
bash /home/morningbell/morningbell/scripts/deploy.sh

# Database console
sudo -u postgres psql morningbell_db

# Nginx status
systemctl status nginx

# View nginx logs
tail -f /var/log/nginx/error.log
```

---

## VM Sizing Guide

| Users | VM Size | Monthly Cost (Hetzner) |
|-------|---------|----------------------|
| 0–50 clients | CX21 (2 vCPU, 4GB) | ~€6 |
| 50–200 clients | CX31 (2 vCPU, 8GB) | ~€11 |
| 200–500 clients | CX41 (4 vCPU, 16GB) | ~€22 |
| 500+ clients | CX51 (8 vCPU, 32GB) | ~€44 |

Start with CX21. Upgrade with one click when needed.

---

## Environment: Done ✓
## Database: PostgreSQL on same VM ✓
## Process manager: PM2 (auto-restarts on crash) ✓
## Web server: Nginx (reverse proxy + SSL) ✓
## SSL: Let's Encrypt (free, auto-renews) ✓
## Backups: Daily gzip dumps, 7-day retention ✓
