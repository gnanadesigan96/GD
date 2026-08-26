#!/usr/bin/env python3
"""Build or update a CloudFront distribution config for the frontend + API.

One distribution serves both: the default behavior points at the S3
frontend bucket, and a `/api/*` behavior points at the backend's API
Gateway HTTP API endpoint. The S3 origin uses Origin Access Control so the
bucket needs no public ("Principal": "*") policy; the API Gateway origin is
just a plain public custom origin (API Gateway's default endpoint is
already public) -- access control there is the app-level
CUR_DASHBOARD_API_KEY, not IAM signing. (An earlier version of this script
routed to a Lambda Function URL via OAC instead; that combination does not
work in this AWS account -- see deploy_backend.sh's top comment.)

Kept as a small Python helper (instead of shell-templated JSON) because the
domain/certificate/api fields are all conditional and this needs to both
build a fresh config and merge into one fetched from the API.

Usage:
  build_distribution_config.py create <bucket> <bucket_domain> <s3_oac_id> <api_domain> [domain_name] [acm_cert_arn]
  build_distribution_config.py merge  <api_domain> [domain_name] [acm_cert_arn]   (reads the existing DistributionConfig JSON on stdin)
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


def api_origin(api_domain):
    # UpdateDistribution validates more strictly than CreateDistribution and
    # rejects an origin missing fields that otherwise have sensible
    # defaults (e.g. "The 'OriginCustomHeaders' field is missing") -- so
    # every field is spelled out explicitly here rather than relying on
    # CloudFront to fill in defaults. No OriginAccessControlId: API
    # Gateway's default endpoint is already public, and access control is
    # the app-level CUR_DASHBOARD_API_KEY instead of IAM signing.
    return {
        "Id": "api-origin",
        "DomainName": api_domain,
        "OriginPath": "",
        "CustomHeaders": {"Quantity": 0, "Items": []},
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
    # As with the origin: UpdateDistribution rejects a behavior missing
    # fields CreateDistribution would default for free (SmoothStreaming,
    # Compress, etc.). All fields below are exactly what CloudFront itself
    # returned for this behavior after accepting it via CreateDistribution.
    return {
        "PathPattern": "/api/*",
        "TargetOriginId": "api-origin",
        "TrustedSigners": {"Enabled": False, "Quantity": 0},
        "TrustedKeyGroups": {"Enabled": False, "Quantity": 0},
        "ViewerProtocolPolicy": "https-only",
        "AllowedMethods": {
            "Quantity": 7,
            "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
            "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
        },
        "SmoothStreaming": False,
        "Compress": False,
        "LambdaFunctionAssociations": {"Quantity": 0},
        "FunctionAssociations": {"Quantity": 0},
        "FieldLevelEncryptionId": "",
        "CachePolicyId": CACHING_DISABLED_POLICY_ID,
        "OriginRequestPolicyId": ALL_VIEWER_EXCEPT_HOST_HEADER_POLICY_ID,
        "GrpcConfig": {"Enabled": False},
    }


def main():
    mode = sys.argv[1]

    if mode == "create":
        bucket, bucket_domain, s3_oac_id, api_domain = sys.argv[2:6]
        domain_name = sys.argv[6] if len(sys.argv) > 6 else ""
        acm_cert_arn = sys.argv[7] if len(sys.argv) > 7 else ""
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
                    api_origin(api_domain),
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
        api_domain = sys.argv[2]
        domain_name = sys.argv[3] if len(sys.argv) > 3 else ""
        acm_cert_arn = sys.argv[4] if len(sys.argv) > 4 else ""
        config = json.load(sys.stdin)

        if domain_name and acm_cert_arn:
            aliases, cert = viewer_certificate(domain_name, acm_cert_arn)
            config["Aliases"] = {"Quantity": len(aliases), "Items": aliases}
            config["ViewerCertificate"] = cert

        origins = config.get("Origins", {"Quantity": 0, "Items": []})
        origins["Items"] = [o for o in origins["Items"] if o["Id"] not in ("lambda-origin", "api-origin")]
        origins["Items"].append(api_origin(api_domain))
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
