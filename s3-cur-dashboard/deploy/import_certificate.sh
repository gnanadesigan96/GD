#!/usr/bin/env bash
# Import an existing certificate + private key into ACM, for use with
# deploy_frontend.sh's DOMAIN_NAME / ACM_CERT_ARN options.
#
# Must run against us-east-1 -- CloudFront only accepts ACM certificates
# from that region, regardless of where the distribution's edge locations
# are. The certificate chain should contain intermediate certificate(s)
# only, not the self-signed root.
#
# The private key never touches this script's own output or logs -- it is
# only ever referenced by file path when calling the AWS CLI.
#
# Usage:
#   CERT_FILE=/path/to/cert.pem \
#   CHAIN_FILE=/path/to/intermediate-chain.pem \
#   KEY_FILE=/path/to/private.key \
#   ./import_certificate.sh
set -euo pipefail

: "${CERT_FILE:?Set CERT_FILE to the leaf certificate PEM file}"
: "${CHAIN_FILE:?Set CHAIN_FILE to the intermediate certificate chain PEM file}"
: "${KEY_FILE:?Set KEY_FILE to the private key file matching CERT_FILE}"

echo "== Verifying the key matches the certificate (no key material is printed) =="
CERT_MODULUS_MD5="$(openssl x509 -noout -modulus -in "$CERT_FILE" | openssl md5)"
KEY_MODULUS_MD5="$(openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5)"
if [ "$CERT_MODULUS_MD5" != "$KEY_MODULUS_MD5" ]; then
  echo "Certificate and private key do not match -- aborting." >&2
  exit 1
fi
echo "Match confirmed."

echo "== Importing into ACM (us-east-1) =="
CERT_ARN="$(aws acm import-certificate \
  --certificate "fileb://${CERT_FILE}" \
  --certificate-chain "fileb://${CHAIN_FILE}" \
  --private-key "fileb://${KEY_FILE}" \
  --region us-east-1 \
  --query 'CertificateArn' --output text)"

cat <<EOF

Certificate imported.

  ACM_CERT_ARN=${CERT_ARN}

Pass this to deploy_frontend.sh along with DOMAIN_NAME to attach it to the
CloudFront distribution:

  DOMAIN_NAME=<your-domain> ACM_CERT_ARN=${CERT_ARN} \\
  LAMBDA_FUNCTION_NAME=<backend-lambda-name> BUCKET=<bucket> ./deploy_frontend.sh

Note: an imported certificate does not auto-renew. Re-run this script with
the renewed cert/key before it expires, then re-run deploy_frontend.sh with
the new ARN.
EOF
