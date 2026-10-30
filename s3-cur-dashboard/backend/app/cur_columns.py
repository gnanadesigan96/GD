"""Resolve the dashboard's required fields against a customer's CUR schema.

CUR column sets vary slightly (blended vs. unblended cost, resource tags,
etc.), and the manifest format itself varies too -- legacy CUR lists each
column as {"category": ..., "name": ...}, while CUR 2.0 (Data Exports) gives
one flat, already-snake_case name per column instead (see _build_lookup).
Rather than hardcode either shape, we match against the manifest's own
column list -- the one part of the schema that's always accurate for the
file we're about to read.
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

# What the same usage would have cost at the public on-demand rate -- CUR
# populates this on every usage line item regardless of how it was actually
# billed, which is what makes it possible to tell how much of a discount
# came from RI/Savings Plan coverage specifically (see discount_by_type in
# duckdb_reader.aggregate): on-demand-equivalent minus what was actually
# paid for that same usage. Only present once an account has ever used RI or
# a Savings Plan, so this is resolved as optional, like the Net* metrics
# above.
_PUBLIC_ON_DEMAND_COST_CANDIDATE = ("pricing", "publicOnDemandCost")


@dataclass
class ResolvedColumn:
    category: str
    name: str
    # True when this was resolved against a CUR 2.0 (Data Exports) manifest,
    # whose columns are already a single flat, snake_case name (e.g.
    # "line_item_unblended_cost") with no separate category field at all --
    # see _build_lookup. Carried on the dataclass (rather than threaded
    # through every call site) because csv_header needs to know which
    # convention this specific export's raw files actually use.
    flat: bool = False

    def athena_name(self) -> str:
        """snake_case name AWS uses for Athena/Parquet CUR exports, e.g. line_item_unblended_cost.

        Also CUR 2.0's own column name directly (flat=True) -- not a
        coincidence: CUR 2.0 standardized on the same flat naming Athena/
        Parquet already used for legacy CUR, just without the category/name
        split in its manifest.
        """
        return f"{_to_snake(self.category)}_{_to_snake(self.name)}"

    def csv_header(self) -> str:
        """Raw header used in a CUR CSV part file.

        Legacy CUR CSV uses "category/Name" (e.g. lineItem/UnblendedCost).
        CUR 2.0's CSV output uses the same flat snake_case name as its
        Parquet/Athena schema instead, unlike legacy CUR's CSV convention.
        """
        if self.flat:
            return self.athena_name()
        return f"{self.category}/{self.name}"


def _to_snake(value: str) -> str:
    s1 = _CAMEL_BOUNDARY_1.sub(r"\1_\2", value)
    return _CAMEL_BOUNDARY_2.sub(r"\1_\2", s1).lower()


def _build_lookup(manifest_columns: list[dict]) -> tuple[dict, bool]:
    """Legacy CUR manifests list each column as {"category": ..., "name":
    ...}; CUR 2.0 (Data Exports) manifests instead give one flat,
    already-snake_case name per column (e.g. "bill_bill_type") with no
    category field -- confirmed against a real Smartsheet CUR 2.0 export,
    whose manifest raised a bare KeyError('category') before this existed.
    A manifest is consistently one format or the other, so checking the
    first column decides it for the whole list.
    """
    is_flat = bool(manifest_columns) and "category" not in manifest_columns[0]
    if is_flat:
        return {c["name"].lower(): c for c in manifest_columns}, True
    return {(c["category"].lower(), c["name"].lower()): c for c in manifest_columns}, False


def _match_candidate(lookup: dict, is_flat: bool, category: str, name: str) -> dict | None:
    if is_flat:
        flat_name = f"{_to_snake(category)}_{_to_snake(name)}"
        return lookup.get(flat_name)
    return lookup.get((category.lower(), name.lower()))


def resolve_columns(manifest_columns: list[dict]) -> dict[str, ResolvedColumn]:
    lookup, is_flat = _build_lookup(manifest_columns)

    resolved: dict[str, ResolvedColumn] = {}
    for field, candidates in _CANDIDATES.items():
        for category, name in candidates:
            if _match_candidate(lookup, is_flat, category, name):
                resolved[field] = ResolvedColumn(category=category, name=name, flat=is_flat)
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
    lookup, is_flat = _build_lookup(manifest_columns)

    metrics: dict[str, ResolvedColumn] = {}
    for metric_name, (category, name) in _COST_METRIC_CANDIDATES:
        if _match_candidate(lookup, is_flat, category, name):
            metrics[metric_name] = ResolvedColumn(category=category, name=name, flat=is_flat)
    return metrics


def resolve_public_on_demand_cost(manifest_columns: list[dict]) -> ResolvedColumn | None:
    lookup, is_flat = _build_lookup(manifest_columns)
    category, name = _PUBLIC_ON_DEMAND_COST_CANDIDATE
    if _match_candidate(lookup, is_flat, category, name):
        return ResolvedColumn(category=category, name=name, flat=is_flat)
    return None
