#!/bin/bash
# MorningBell VM Setup Script
# Supports Ubuntu 22.04 and 24.04 LTS
# Usage: curl -sL <your-raw-url>/setup-vm.sh | sudo bash

set -e

UBUNTU_VERSION=$(lsb_release -rs)
echo "============================================"
echo "  MorningBell VM Setup — Ubuntu $UBUNTU_VERSION"
echo "============================================"

# --- System update ---
apt-get update -y && apt-get upgrade -y
apt-get install -y curl git unzip ufw nginx certbot python3-certbot-nginx build-essential gnupg2 lsb-release

# --- Node.js 20 LTS ---
echo "Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
node -v && npm -v

# --- PM2 (process manager) ---
echo "Installing PM2..."
npm install -g pm2

# --- PostgreSQL 16 ---
echo "Installing PostgreSQL 16..."
apt-get install -y gnupg curl
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
apt-get update -y
apt-get install -y postgresql-16 postgresql-client-16

# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# --- Create DB user and database ---
echo "Setting up PostgreSQL database..."
DB_PASSWORD=$(openssl rand -base64 24 | tr -d '=/+' | head -c 32)

sudo -u postgres psql <<SQL
CREATE USER morningbell WITH PASSWORD '$DB_PASSWORD';
CREATE DATABASE morningbell_db OWNER morningbell;
GRANT ALL PRIVILEGES ON DATABASE morningbell_db TO morningbell;
SQL

echo ""
echo "============================================"
echo "  DATABASE CREDENTIALS — SAVE THESE NOW"
echo "============================================"
echo "  DB_USER:     morningbell"
echo "  DB_PASSWORD: $DB_PASSWORD"
echo "  DB_NAME:     morningbell_db"
echo "  DATABASE_URL: postgresql://morningbell:$DB_PASSWORD@localhost:5432/morningbell_db"
echo "============================================"
echo ""

# Save credentials to file
cat > /root/db-credentials.txt <<EOF
DB_USER=morningbell
DB_PASSWORD=$DB_PASSWORD
DB_NAME=morningbell_db
DATABASE_URL=postgresql://morningbell:$DB_PASSWORD@localhost:5432/morningbell_db
EOF
chmod 600 /root/db-credentials.txt
echo "Saved to /root/db-credentials.txt"

# --- Create app user ---
echo "Creating morningbell system user..."
id -u morningbell &>/dev/null || useradd -m -s /bin/bash morningbell

# --- Firewall ---
echo "Configuring UFW firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo ""
echo "============================================"
echo "  VM setup complete!"
echo "  Next: run deploy.sh to deploy the app"
echo "============================================"
