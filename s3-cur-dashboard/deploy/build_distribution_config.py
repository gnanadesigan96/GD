#!/usr/bin/env python3
"""Build or update a CloudFront distribution config for the frontend.

Kept as a small Python helper (instead of shell-templated JSON) because the
domain/certificate fields are conditional and this needs to both build a
fresh config and merge into an existing one fetched from the API.

Usage:
  build_distribution_config.py create <bucket> <bucket_domain> <oac_id> [domain_name] [acm_cert_arn]
  build_distribution_config.py merge  [domain_name] [acm_cert_arn]   (reads the existing DistributionConfig JSON on stdin)
"""
import json
import sys


def viewer_certificate(domain_name, acm_cert_arn):
    if domain_name and acm_cert_arn:
        return [domain_name], {
            "ACMCertificateArn": acm_cert_arn,
            "SSLSupportMethod": "sni-only",
            "MinimumProtocolVersion": "TLSv1.2_2021",
            "CertificateSource": "acm",
        }
    return [], {"CloudFrontDefaultCertificate": True}


def main():
    mode = sys.argv[1]

    if mode == "create":
        bucket, bucket_domain, oac_id = sys.argv[2], sys.argv[3], sys.argv[4]
        domain_name = sys.argv[5] if len(sys.argv) > 5 else ""
        acm_cert_arn = sys.argv[6] if len(sys.argv) > 6 else ""
        aliases, cert = viewer_certificate(domain_name, acm_cert_arn)

        config = {
            "CallerReference": f"{bucket}-frontend",
            "Comment": "S3 CUR dashboard frontend",
            "Enabled": True,
            "PriceClass": "PriceClass_100",
            "DefaultRootObject": "index.html",
            "Aliases": {"Quantity": len(aliases), "Items": aliases},
            "Origins": {
                "Quantity": 1,
                "Items": [
                    {
                        "Id": "s3-origin",
                        "DomainName": bucket_domain,
                        "S3OriginConfig": {"OriginAccessIdentity": ""},
                        "OriginAccessControlId": oac_id,
                    }
                ],
            },
            "DefaultCacheBehavior": {
                "TargetOriginId": "s3-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
            },
            "CustomErrorResponses": {
                "Quantity": 2,
                "Items": [
                    {"ErrorCode": 403, "ResponseCode": "200", "ResponsePagePath": "/index.html"},
                    {"ErrorCode": 404, "ResponseCode": "200", "ResponsePagePath": "/index.html"},
                ],
            },
            "ViewerCertificate": cert,
        }
        print(json.dumps(config))

    elif mode == "merge":
        domain_name = sys.argv[2] if len(sys.argv) > 2 else ""
        acm_cert_arn = sys.argv[3] if len(sys.argv) > 3 else ""
        config = json.load(sys.stdin)
        if domain_name and acm_cert_arn:
            aliases, cert = viewer_certificate(domain_name, acm_cert_arn)
            config["Aliases"] = {"Quantity": len(aliases), "Items": aliases}
            config["ViewerCertificate"] = cert
        print(json.dumps(config))

    else:
        sys.exit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()
