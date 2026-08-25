#!/usr/bin/env python3
"""Build or update a CloudFront distribution config for the frontend + API.

One distribution serves both: the default behavior points at the S3
frontend bucket, and a `/api/*` behavior points at the backend Lambda's
Function URL. Both origins use Origin Access Control so neither the bucket
nor the Function URL needs a public ("Principal": "*") resource policy --
CloudFront signs requests to each on the distribution's behalf.

Kept as a small Python helper (instead of shell-templated JSON) because the
domain/certificate/lambda fields are all conditional and this needs to both
build a fresh config and merge into one fetched from the API.

Usage:
  build_distribution_config.py create <bucket> <bucket_domain> <s3_oac_id> <lambda_domain> <lambda_oac_id> [domain_name] [acm_cert_arn]
  build_distribution_config.py merge  <lambda_domain> <lambda_oac_id> [domain_name] [acm_cert_arn]   (reads the existing DistributionConfig JSON on stdin)
"""
import json
import sys

CACHING_DISABLED_POLICY_ID = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
ALL_VIEWER_EXCEPT_HOST_HEADER_POLICY_ID = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
CACHING_OPTIMIZED_POLICY_ID = "658327ea-f89d-4fab-a63d-7e88639e58f6"


def viewer_certificate(domain_name, acm_cert_arn):
    if domain_name and acm_cert_arn:
        return [domain_name], {
            "ACMCertificateArn": acm_cert_arn,
            "SSLSupportMethod": "sni-only",
            "MinimumProtocolVersion": "TLSv1.2_2021",
            "CertificateSource": "acm",
        }
    return [], {"CloudFrontDefaultCertificate": True}


def lambda_origin(lambda_domain, lambda_oac_id):
    # UpdateDistribution validates more strictly than CreateDistribution and
    # rejects an origin missing fields that otherwise have sensible
    # defaults (e.g. "The 'OriginCustomHeaders' field is missing") -- so
    # every field is spelled out explicitly here rather than relying on
    # CloudFront to fill in defaults.
    return {
        "Id": "lambda-origin",
        "DomainName": lambda_domain,
        "OriginPath": "",
        "OriginAccessControlId": lambda_oac_id,
        "OriginCustomHeaders": {"Quantity": 0},
        "ConnectionAttempts": 3,
        "ConnectionTimeout": 10,
        "OriginShield": {"Enabled": False},
        "CustomOriginConfig": {
            "HTTPPort": 80,
            "HTTPSPort": 443,
            "OriginProtocolPolicy": "https-only",
            "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]},
            "OriginReadTimeout": 30,
            "OriginKeepaliveTimeout": 5,
        },
    }


def api_cache_behavior():
    return {
        "PathPattern": "/api/*",
        "TargetOriginId": "lambda-origin",
        "ViewerProtocolPolicy": "https-only",
        "AllowedMethods": {
            "Quantity": 7,
            "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
            "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
        },
        "CachePolicyId": CACHING_DISABLED_POLICY_ID,
        "OriginRequestPolicyId": ALL_VIEWER_EXCEPT_HOST_HEADER_POLICY_ID,
    }


def main():
    mode = sys.argv[1]

    if mode == "create":
        bucket, bucket_domain, s3_oac_id, lambda_domain, lambda_oac_id = sys.argv[2:7]
        domain_name = sys.argv[7] if len(sys.argv) > 7 else ""
        acm_cert_arn = sys.argv[8] if len(sys.argv) > 8 else ""
        aliases, cert = viewer_certificate(domain_name, acm_cert_arn)

        config = {
            "CallerReference": f"{bucket}-frontend",
            "Comment": "S3 CUR dashboard frontend + API",
            "Enabled": True,
            "PriceClass": "PriceClass_100",
            "DefaultRootObject": "index.html",
            "Aliases": {"Quantity": len(aliases), "Items": aliases},
            "Origins": {
                "Quantity": 2,
                "Items": [
                    {
                        "Id": "s3-origin",
                        "DomainName": bucket_domain,
                        "S3OriginConfig": {"OriginAccessIdentity": ""},
                        "OriginAccessControlId": s3_oac_id,
                    },
                    lambda_origin(lambda_domain, lambda_oac_id),
                ],
            },
            "DefaultCacheBehavior": {
                "TargetOriginId": "s3-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                "CachePolicyId": CACHING_OPTIMIZED_POLICY_ID,
            },
            "CacheBehaviors": {"Quantity": 1, "Items": [api_cache_behavior()]},
            # No CustomErrorResponses: this app has a single route (no
            # client-side routing to fall back for), and a distribution-wide
            # 403/404 -> index.html rule would silently mask real errors
            # from the /api/* Lambda origin behind the frontend page.
            "CustomErrorResponses": {"Quantity": 0, "Items": []},
            "ViewerCertificate": cert,
        }
        print(json.dumps(config))

    elif mode == "merge":
        lambda_domain, lambda_oac_id = sys.argv[2], sys.argv[3]
        domain_name = sys.argv[4] if len(sys.argv) > 4 else ""
        acm_cert_arn = sys.argv[5] if len(sys.argv) > 5 else ""
        config = json.load(sys.stdin)

        if domain_name and acm_cert_arn:
            aliases, cert = viewer_certificate(domain_name, acm_cert_arn)
            config["Aliases"] = {"Quantity": len(aliases), "Items": aliases}
            config["ViewerCertificate"] = cert

        origins = config.get("Origins", {"Quantity": 0, "Items": []})
        origins["Items"] = [o for o in origins["Items"] if o["Id"] != "lambda-origin"]
        origins["Items"].append(lambda_origin(lambda_domain, lambda_oac_id))
        origins["Quantity"] = len(origins["Items"])
        config["Origins"] = origins

        behaviors = config.get("CacheBehaviors", {"Quantity": 0, "Items": []})
        behaviors["Items"] = [b for b in behaviors.get("Items", []) if b["PathPattern"] != "/api/*"]
        behaviors["Items"].append(api_cache_behavior())
        behaviors["Quantity"] = len(behaviors["Items"])
        config["CacheBehaviors"] = behaviors

        # Drop any 403/404 -> index.html rule from an earlier version of
        # this script: it's distribution-wide, so it would mask real errors
        # from the /api/* Lambda origin behind the frontend page.
        config["CustomErrorResponses"] = {"Quantity": 0, "Items": []}

        print(json.dumps(config))

    else:
        sys.exit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()
