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

export function DrilldownPanel({ title, subtitle, rows, availableCostMetrics, formatMoney, onClose }: DrilldownPanelProps) {
  const [metric, setMetric] = useState(availableCostMetrics[0] ?? "");
  const [dimension, setDimension] = useState<Dimension>("product_category");
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const totals = new Map<string, number>();
    for (const row of rows) {
      const key = row[dimension];
      totals.set(key, (totals.get(key) ?? 0) + (row.costs[metric] ?? 0));
    }
    return Array.from(totals.entries())
      .map(([label, cost]) => ({ label, cost }))
      .sort((a, b) => b.cost - a.cost);
  }, [rows, dimension, metric]);

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
    return otherDims.map((d) => {
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
          </tr>
        </thead>
        <tbody>
          {visible.length === 0 && (
            <tr>
              <td colSpan={2} className="empty">
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
                </tr>
                {isExpanded && breakdown && (
                  <tr className="drilldown-row">
                    <td colSpan={2} className="drilldown-breakdown-cell">
                      <div className="drilldown-breakdown">
                        <p className="drilldown-breakdown-hint">
                          Breakdown of “{g.label}” ({formatMoney(g.cost)}) by the other two dimensions:
                        </p>
                        <div className="drilldown-breakdown-grid">
                          {breakdown.map(({ dim, entries }) => (
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
                        </div>
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
    </div>
  );
}
