import { Fragment, useMemo, useState } from "react";
import { metricLabel } from "../lib/format";
import type { DimensionalCosts } from "../types";

interface DrilldownPanelProps {
  title: string;
  subtitle: string;
  rows: DimensionalCosts[];
  availableCostMetrics: string[];
  formatMoney: (value: number) => string;
  onClose: () => void;
}

type Dimension = "product_category" | "resource_category" | "charge_type";

const DIMENSIONS: { key: Dimension; label: string }[] = [
  { key: "product_category", label: "Product Category" },
  { key: "resource_category", label: "Resource Category" },
  { key: "charge_type", label: "Charge Type" },
];

// AWS's own CUR export, not this dashboard, leaves these fields blank for
// certain charge types that aren't tied to one specific service -- most
// often enterprise/negotiated discounts, credits, refunds, and support fee
// credits applied account-wide. Shown only when "unknown" actually appears
// in the current view, since it usually doesn't.
const UNKNOWN_EXPLANATIONS: Record<Dimension, string> = {
  product_category:
    "“unknown” means AWS's CUR export didn't record a product/service name for these line items -- typically account-wide discounts, credits, or refunds rather than usage of a specific AWS service.",
  resource_category:
    "“unknown” means AWS's CUR export didn't record a resource category for these line items -- typically account-wide discounts, credits, or refunds rather than a specific resource type.",
  charge_type:
    "“unknown” means AWS's CUR export didn't record a charge type for these line items.",
};

const OTHER_DIMENSIONS: Record<Dimension, { key: Dimension; label: string }[]> = {
  product_category: [DIMENSIONS[1], DIMENSIONS[2]],
  resource_category: [DIMENSIONS[0], DIMENSIONS[2]],
  charge_type: [DIMENSIONS[0], DIMENSIONS[1]],
};

// NetUnblendedCost is AWS's post-discount equivalent of UnblendedCost,
// computed per line item rather than only in aggregate -- so unlike the
// "EdpDiscount" charge type (which usually carries no resource category of
// its own), unblended-vs-net-unblended can be compared at any dimension,
// including resource category. The gap between them reflects any negotiated
// pricing on the bill, not exclusively EDP specifically, but for an account
// whose only negotiated agreement is EDP, that's the same thing in practice.
const DISCOUNT_METRICS_REQUIRED = ["unblended_cost", "net_unblended_cost"] as const;

// Mirrors duckdb_reader.aggregate's discount_by_type bucketing exactly, so
// a resource category's breakdown here matches the whole-bill "Discount by
// type" panel's logic -- see that function's comments for why each bucket
// is grouped the way it is (EDP/SPP/private-rate/bundled discount lines
// already carry the discount amount directly; RI/Savings Plan savings need
// public_on_demand_cost minus what was actually paid instead).
const EDP_CHARGE_TYPES = new Set(["EdpDiscount"]);
const SPP_CHARGE_TYPES = new Set(["DistributorDiscount", "SppDiscount"]);
const PRIVATE_RATE_CHARGE_TYPES = new Set(["PrivateRateDiscount"]);
const BUNDLED_CHARGE_TYPES = new Set(["BundledDiscount"]);
const RI_CHARGE_TYPES = new Set(["DiscountedUsage", "RIFee", "RIUpfrontFee"]);
const SAVINGS_PLAN_CHARGE_TYPES = new Set([
  "SavingsPlanCoveredUsage",
  "SavingsPlanNegation",
  "SavingsPlanRecurringFee",
  "SavingsPlanUpfrontFee",
]);

const DISCOUNT_TYPE_LABELS: Record<string, string> = {
  edp: "Enterprise Discount Program (EDP)",
  spp: "SPP / distributor discount",
  private_rate: "Private Pricing Agreement",
  bundled: "Bundled discount",
  ri: "Reserved Instances",
  savings_plan: "Savings Plans",
};

interface DiscountTypeEntry {
  label: string;
  amount: number;
  estimated: boolean;
}

function bucketDiscountByType(rows: DimensionalCosts[]): DiscountTypeEntry[] {
  const direct: Record<string, number> = {};
  let riActual = 0;
  let riPod = 0;
  let riPodSeen = false;
  let spActual = 0;
  let spPod = 0;
  let spPodSeen = false;

  for (const row of rows) {
    const cost = row.costs.unblended_cost ?? 0;
    const pod = row.public_on_demand_cost;
    const chargeType = row.charge_type;
    if (EDP_CHARGE_TYPES.has(chargeType)) {
      direct.edp = (direct.edp ?? 0) - cost;
    } else if (SPP_CHARGE_TYPES.has(chargeType)) {
      direct.spp = (direct.spp ?? 0) - cost;
    } else if (PRIVATE_RATE_CHARGE_TYPES.has(chargeType)) {
      direct.private_rate = (direct.private_rate ?? 0) - cost;
    } else if (BUNDLED_CHARGE_TYPES.has(chargeType)) {
      direct.bundled = (direct.bundled ?? 0) - cost;
    } else if (RI_CHARGE_TYPES.has(chargeType)) {
      riActual += cost;
      if (pod !== null) {
        riPod += pod;
        riPodSeen = true;
      }
    } else if (SAVINGS_PLAN_CHARGE_TYPES.has(chargeType)) {
      spActual += cost;
      if (pod !== null) {
        spPod += pod;
        spPodSeen = true;
      }
    }
  }

  const entries: DiscountTypeEntry[] = [];
  for (const [key, amount] of Object.entries(direct)) {
    if (amount) entries.push({ label: DISCOUNT_TYPE_LABELS[key] ?? key, amount, estimated: false });
  }
  if (riPodSeen) entries.push({ label: DISCOUNT_TYPE_LABELS.ri, amount: riPod - riActual, estimated: true });
  if (spPodSeen) entries.push({ label: DISCOUNT_TYPE_LABELS.savings_plan, amount: spPod - spActual, estimated: true });
  return entries;
}

export function DrilldownPanel({ title, subtitle, rows, availableCostMetrics, formatMoney, onClose }: DrilldownPanelProps) {
  const [metric, setMetric] = useState(availableCostMetrics[0] ?? "");
  const [dimension, setDimension] = useState<Dimension>("product_category");
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const hasDiscountMetrics = DISCOUNT_METRICS_REQUIRED.every((m) => availableCostMetrics.includes(m));

  const grouped = useMemo(() => {
    const totals = new Map<string, { cost: number; unblended: number; netUnblended: number }>();
    for (const row of rows) {
      const key = row[dimension];
      const entry = totals.get(key) ?? { cost: 0, unblended: 0, netUnblended: 0 };
      entry.cost += row.costs[metric] ?? 0;
      entry.unblended += row.costs.unblended_cost ?? 0;
      entry.netUnblended += row.costs.net_unblended_cost ?? 0;
      totals.set(key, entry);
    }
    return Array.from(totals.entries())
      .map(([label, { cost, unblended, netUnblended }]) => ({
        label,
        cost,
        discountPct: hasDiscountMetrics && unblended > 0 ? ((unblended - netUnblended) / unblended) * 100 : null,
      }))
      .sort((a, b) => b.cost - a.cost);
  }, [rows, dimension, metric, hasDiscountMetrics]);

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return term ? grouped.filter((g) => g.label.toLowerCase().includes(term)) : grouped;
  }, [grouped, search]);

  const visibleTotal = visible.reduce((sum, g) => sum + g.cost, 0);
  const dimensionLabel = DIMENSIONS.find((d) => d.key === dimension)?.label ?? "";
  const unknownRow = visible.find((g) => g.label === "unknown");
  const otherDims = OTHER_DIMENSIONS[dimension];

  const breakdown = useMemo(() => {
    if (!expanded) return null;
    const matching = rows.filter((r) => r[dimension] === expanded);
    const dims = otherDims.map((d) => {
      const totals = new Map<string, number>();
      for (const row of matching) {
        const key = row[d.key];
        totals.set(key, (totals.get(key) ?? 0) + (row.costs[metric] ?? 0));
      }
      const entries = Array.from(totals.entries())
        .map(([label, cost]) => ({ label, cost }))
        .sort((a, b) => b.cost - a.cost);
      return { dim: d, entries };
    });
    // Which discount program applied is only meaningful broken out by
    // resource category (EDP/SPP/private-rate/bundled discount lines are
    // account-wide and carry no resource category of their own -- they'll
    // show up under "unknown" -- so this stays scoped to that dimension
    // rather than showing an always-empty column elsewhere).
    const discountByType = dimension === "resource_category" ? bucketDiscountByType(matching) : [];
    return { dims, discountByType };
  }, [expanded, rows, dimension, otherDims, metric]);

  return (
    <div className="drilldown">
      <div className="drilldown-head">
        <div>
          <span className="drilldown-title">{title}</span>
          <span className="drilldown-sub">{subtitle}</span>
        </div>
        <button className="drilldown-close" onClick={onClose} aria-label="Close drill-down">
          Close
        </button>
      </div>

      {availableCostMetrics.length > 0 && (
        <div className="drilldown-step">
          <span className="drilldown-step-label">1. Cost metric</span>
          <div className="drilldown-pills">
            {availableCostMetrics.map((m) => (
              <button
                key={m}
                className={m === metric ? "metric-pill active" : "metric-pill"}
                onClick={() => {
                  setMetric(m);
                  setExpanded(null);
                }}
              >
                {metricLabel(m)}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="drilldown-step">
        <span className="drilldown-step-label">2. View by</span>
        <div className="drilldown-pills">
          {DIMENSIONS.map((d) => (
            <button
              key={d.key}
              className={d.key === dimension ? "metric-pill active" : "metric-pill"}
              onClick={() => {
                setDimension(d.key);
                setExpanded(null);
              }}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <div className="drilldown-filter">
        <label>
          Search {dimensionLabel.toLowerCase()}
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setExpanded(null);
            }}
            placeholder={`Filter by ${dimensionLabel.toLowerCase()}...`}
          />
        </label>
        <span className="drilldown-total">
          {metricLabel(metric || "cost")} total: <strong>{formatMoney(visibleTotal)}</strong>
        </span>
      </div>

      <p className="drilldown-row-hint">Click a row to break it down by {otherDims.map((d) => d.label).join(" and ")}.</p>

      <table className="drilldown-table">
        <thead>
          <tr>
            <th>{dimensionLabel}</th>
            <th>{metric ? metricLabel(metric) : "Cost"}</th>
            {hasDiscountMetrics && <th>Discount %</th>}
          </tr>
        </thead>
        <tbody>
          {visible.length === 0 && (
            <tr>
              <td colSpan={hasDiscountMetrics ? 3 : 2} className="empty">
                {search ? "No matches for that search." : "No line items for this selection."}
              </td>
            </tr>
          )}
          {visible.map((g) => {
            const isExpanded = g.label === expanded;
            return (
              <Fragment key={g.label}>
                <tr
                  className="drilldown-row-clickable"
                  onClick={() => setExpanded(isExpanded ? null : g.label)}
                >
                  <td>{g.label}</td>
                  <td>{formatMoney(g.cost)}</td>
                  {hasDiscountMetrics && <td>{g.discountPct === null ? "—" : `${g.discountPct.toFixed(1)}%`}</td>}
                </tr>
                {isExpanded && breakdown && (
                  <tr className="drilldown-row">
                    <td colSpan={hasDiscountMetrics ? 3 : 2} className="drilldown-breakdown-cell">
                      <div className="drilldown-breakdown">
                        <p className="drilldown-breakdown-hint">
                          Breakdown of "{g.label}" ({formatMoney(g.cost)}) by the other two dimensions:
                        </p>
                        <div className="drilldown-breakdown-grid">
                          {breakdown.dims.map(({ dim, entries }) => (
                            <div key={dim.key} className="drilldown-breakdown-col">
                              <span className="drilldown-breakdown-col-label">{dim.label}</span>
                              <table className="drilldown-table">
                                <tbody>
                                  {entries.map((e) => (
                                    <tr key={e.label}>
                                      <td>{e.label}</td>
                                      <td>{formatMoney(e.cost)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ))}
                          {breakdown.discountByType.length > 0 && (
                            <div className="drilldown-breakdown-col">
                              <span className="drilldown-breakdown-col-label">Discount Type</span>
                              <table className="drilldown-table">
                                <tbody>
                                  {breakdown.discountByType.map((e) => (
                                    <tr key={e.label}>
                                      <td>
                                        {e.label}
                                        {e.estimated ? " *" : ""}
                                      </td>
                                      <td>{formatMoney(e.amount)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                        {breakdown.discountByType.some((e) => e.estimated) && (
                          <p className="drilldown-breakdown-hint">
                            * Reserved Instance / Savings Plan figures are estimated as list-price-equivalent cost
                            minus what was actually paid for this resource category's covered usage.
                          </p>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>

      {unknownRow && (
        <p className="drilldown-note">
          <strong>“unknown”</strong> ({formatMoney(unknownRow.cost)}): {UNKNOWN_EXPLANATIONS[dimension]}{" "}
          {dimension !== "charge_type" && 'Switch to "Charge Type" above to see what kind of charges these are.'}
        </p>
      )}

      {hasDiscountMetrics && (
        <p className="drilldown-note">
          <strong>Discount %</strong> is (unblended cost − net unblended cost) ÷ unblended cost for each row --
          AWS computes net unblended cost per line item after negotiated pricing, so this reflects any negotiated
          discount on the bill (EDP included) at whichever level you're viewing, not just the overall total.
        </p>
      )}
    </div>
  );
}
