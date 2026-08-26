"""Resolve the dashboard's required fields against a customer's CUR schema.

CUR column sets vary slightly (blended vs. unblended cost, resource tags,
CUR 2.0 renames, etc.), so instead of hardcoding column names we match
against the manifest's own column list -- the one part of the schema that's
always accurate for the file we're about to read.
"""

import re
from dataclasses import dataclass
from fastapi import HTTPException

_CAMEL_BOUNDARY_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_BOUNDARY_2 = re.compile(r"([a-z0-9])([A-Z])")

# (category, name) candidates in priority order for each field the dashboard needs.
_CANDIDATES = {
    "cost": [("lineItem", "UnblendedCost"), ("lineItem", "BlendedCost"), ("cost", "UnblendedCost")],
    "service": [("product", "ProductName"), ("lineItem", "ProductCode"), ("product", "servicecode")],
    "usage_start_date": [("lineItem", "UsageStartDate")],
    "account_id": [("lineItem", "UsageAccountId"), ("bill", "PayerAccountId")],
    "currency": [("lineItem", "CurrencyCode")],
    # Drill-down dimensions (optional -- not every export has these, so they
    # aren't in _REQUIRED). "Product Category" reuses "service" above rather
    # than resolving separately, since they're the same field.
    "resource_category": [("product", "productFamily")],
    "charge_type": [("lineItem", "LineItemType")],
}

_REQUIRED = {"cost", "service", "usage_start_date", "account_id"}

# Every column CUR commonly uses for "cost", in priority/display order. Not
# all of these exist in every export (Net* columns usually only appear once
# an account has Reserved Instances or Savings Plans) -- resolve_cost_metrics
# returns whichever subset is actually present, so the drill-down UI only
# ever offers metrics that exist in this specific bill.
_COST_METRIC_CANDIDATES = [
    ("unblended_cost", ("lineItem", "UnblendedCost")),
    ("blended_cost", ("lineItem", "BlendedCost")),
    ("net_unblended_cost", ("lineItem", "NetUnblendedCost")),
    ("net_amortized_cost", ("lineItem", "NetAmortizedCost")),
    ("amortized_cost", ("lineItem", "AmortizedCost")),
]


@dataclass
class ResolvedColumn:
    category: str
    name: str

    def athena_name(self) -> str:
        """snake_case name AWS uses for Athena/Parquet CUR exports, e.g. line_item_unblended_cost."""
        return f"{_to_snake(self.category)}_{_to_snake(self.name)}"

    def csv_header(self) -> str:
        """Raw header used in legacy CUR CSV part files, e.g. lineItem/UnblendedCost."""
        return f"{self.category}/{self.name}"


def _to_snake(value: str) -> str:
    s1 = _CAMEL_BOUNDARY_1.sub(r"\1_\2", value)
    return _CAMEL_BOUNDARY_2.sub(r"\1_\2", s1).lower()


def resolve_columns(manifest_columns: list[dict]) -> dict[str, ResolvedColumn]:
    lookup = {(c["category"].lower(), c["name"].lower()): c for c in manifest_columns}

    resolved: dict[str, ResolvedColumn] = {}
    for field, candidates in _CANDIDATES.items():
        for category, name in candidates:
            match = lookup.get((category.lower(), name.lower()))
            if match:
                resolved[field] = ResolvedColumn(category=match["category"], name=match["name"])
                break

    missing = _REQUIRED - resolved.keys()
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CUR manifest is missing required column(s) for: {', '.join(sorted(missing))}",
        )
    return resolved


def resolve_cost_metrics(manifest_columns: list[dict]) -> dict[str, ResolvedColumn]:
    """Every cost-like column this specific export actually has, keyed by a
    stable metric name (e.g. "net_unblended_cost") for the drill-down view.
    Unlike resolve_columns' "cost" field (which picks one winner to display
    everywhere else), this returns however many of them exist -- a bill
    without Reserved Instances/Savings Plans typically only has
    unblended_cost and blended_cost; one that does usually adds the Net*
    variants too.
    """
    lookup = {(c["category"].lower(), c["name"].lower()): c for c in manifest_columns}

    metrics: dict[str, ResolvedColumn] = {}
    for metric_name, (category, name) in _COST_METRIC_CANDIDATES:
        match = lookup.get((category.lower(), name.lower()))
        if match:
            metrics[metric_name] = ResolvedColumn(category=match["category"], name=match["name"])
    return metrics
