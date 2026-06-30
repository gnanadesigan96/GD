#!/bin/bash
# Setup SSL certificate with Let's Encrypt
# Usage: bash setup-ssl.sh yourdomain.com your@email.com

set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
  echo "Usage: bash setup-ssl.sh yourdomain.com your@email.com"
  exit 1
fi

echo "Setting up SSL for $DOMAIN..."

# Copy nginx config
sed "s/morningbell.yourdomain.com/$DOMAIN/g" /home/morningbell/morningbell/scripts/nginx.conf > /etc/nginx/sites-available/morningbell

# Enable site
ln -sf /etc/nginx/sites-available/morningbell /etc/nginx/sites-enabled/morningbell
rm -f /etc/nginx/sites-enabled/default

# Test nginx config (temporarily comment out SSL lines)
sed -i 's/listen 443/# listen 443/' /etc/nginx/sites-available/morningbell
sed -i 's/return 301/# return 301/' /etc/nginx/sites-available/morningbell

# Add a temp HTTP server block for certbot challenge
cat > /tmp/certbot-nginx.conf <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    root /var/www/html;
}
EOF

nginx -t && systemctl reload nginx

# Get certificate
certbot --nginx -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email --redirect

# Restore full nginx config
sed "s/morningbell.yourdomain.com/$DOMAIN/g" /home/morningbell/morningbell/scripts/nginx.conf > /etc/nginx/sites-available/morningbell

nginx -t && systemctl reload nginx

echo ""
echo "SSL setup complete for $DOMAIN"
echo "Your app is now available at https://$DOMAIN"
