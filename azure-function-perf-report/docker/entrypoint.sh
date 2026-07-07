#!/bin/bash
set -e

echo "============================================"
echo "CoreStack Performance Report — Container Run"
echo "============================================"
echo "Time (UTC): $(date -u '+%Y-%m-%d %H:%M:%S')"

# ── 1. Start OpenVPN ─────────────────────────────────────────
echo ""
echo "[1/4] Starting OpenVPN..."

mkdir -p /dev/net
if [ ! -c /dev/net/tun ]; then
    mknod /dev/net/tun c 10 200
    chmod 600 /dev/net/tun
fi

openvpn --config /etc/openvpn/client.ovpn \
        --daemon \
        --log /var/log/openvpn.log \
        --writepid /var/run/openvpn.pid

# ── 2. Wait for VPN connection ───────────────────────────────
echo "[2/4] Waiting for VPN tunnel to establish..."

MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if ip addr show tun0 >/dev/null 2>&1; then
        echo "       VPN connected! (tun0 up after ${ELAPSED}s)"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "ERROR: VPN did not connect within ${MAX_WAIT}s"
    echo "--- OpenVPN log ---"
    cat /var/log/openvpn.log
    exit 1
fi

# Quick connectivity check — ping first MongoDB host
echo "       Testing connectivity to MongoDB (4.213.1.249:27017)..."
if timeout 10 bash -c 'echo > /dev/tcp/4.213.1.249/27017' 2>/dev/null; then
    echo "       MongoDB reachable!"
else
    echo "WARN:  Cannot reach 4.213.1.249:27017 — report may have errors"
fi

# ── 3. Run the report ────────────────────────────────────────
echo ""
echo "[3/4] Running performance report generator..."
python3 /app/run_report.py

# ── 4. Stop OpenVPN ──────────────────────────────────────────
echo ""
echo "[4/4] Stopping OpenVPN..."
if [ -f /var/run/openvpn.pid ]; then
    kill "$(cat /var/run/openvpn.pid)" 2>/dev/null || true
fi

echo ""
echo "Done."
