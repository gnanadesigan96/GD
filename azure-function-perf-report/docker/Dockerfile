FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openvpn \
        iproute2 \
        iputils-ping \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY perf_report.py .
COPY sharepoint_upload.py .
COPY run_report.py .
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# VPN config is mounted at runtime, not baked into the image
# Mount your .ovpn file to /etc/openvpn/client.ovpn

ENTRYPOINT ["/entrypoint.sh"]
