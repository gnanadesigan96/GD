#!/bin/bash
# MorningBell Deployment Script
# Run on the VM as root or morningbell user AFTER setup-vm.sh
# Usage: bash deploy.sh

set -e

APP_DIR="/home/morningbell/morningbell"
REPO_URL="https://github.com/gnanadesigan96/GD.git"
BRANCH="claude/sweet-planck-2o0zu0"
APP_SUBDIR="morningbell"

echo "============================================"
echo "  MorningBell Deploy"
echo "============================================"

# --- Clone or pull repo ---
if [ -d "$APP_DIR" ]; then
  echo "Updating existing repo..."
  cd "$APP_DIR"
  git fetch origin "$BRANCH"
  git reset --hard "origin/$BRANCH"
else
  echo "Cloning repo..."
  mkdir -p /home/morningbell
  git clone --branch "$BRANCH" "$REPO_URL" /home/morningbell/GD
  mv /home/morningbell/GD/"$APP_SUBDIR" "$APP_DIR"
fi

cd "$APP_DIR"

# --- Check .env exists ---
if [ ! -f ".env" ]; then
  echo ""
  echo "ERROR: .env file not found!"
  echo "Copy .env.example to .env and fill in all values before deploying."
  echo ""
  echo "  cp .env.example .env && nano .env"
  echo ""
  exit 1
fi

# --- Install dependencies ---
echo "Installing dependencies..."
npm ci --production=false

# --- Generate Prisma client ---
echo "Generating Prisma client..."
npx prisma generate

# --- Run DB migrations ---
echo "Running database migrations..."
npx prisma migrate deploy

# --- Build Next.js ---
echo "Building application..."
npm run build

# --- Set permissions ---
chown -R morningbell:morningbell "$APP_DIR"

# --- Start/Restart with PM2 ---
echo "Starting with PM2..."
if pm2 describe morningbell > /dev/null 2>&1; then
  pm2 restart morningbell
else
  pm2 start npm --name "morningbell" -- start
fi

pm2 save

echo ""
echo "============================================"
echo "  Deploy complete! App running on port 3000"
echo "  PM2 status: pm2 status"
echo "  App logs:   pm2 logs morningbell"
echo "============================================"
