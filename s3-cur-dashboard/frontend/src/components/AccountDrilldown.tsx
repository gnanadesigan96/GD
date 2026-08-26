import { useMemo, useState } from "react";
import type { DrilldownRow } from "../types";

interface AccountDrilldownProps {
  accountId: string;
  rows: DrilldownRow[];
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

function metricLabel(metric: string): string {
  // "net_unblended_cost" -> "Net Unblended Cost"
  return metric
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function AccountDrilldown({ accountId, rows, availableCostMetrics, formatMoney, onClose }: AccountDrilldownProps) {
  const [metric, setMetric] = useState(availableCostMetrics[0] ?? "");
  const [dimension, setDimension] = useState<Dimension>("product_category");
  const [search, setSearch] = useState("");

  const accountRows = useMemo(() => rows.filter((r) => r.account_id === accountId), [rows, accountId]);

  const grouped = useMemo(() => {
    const totals = new Map<string, number>();
    for (const row of accountRows) {
      const key = row[dimension];
      totals.set(key, (totals.get(key) ?? 0) + (row.costs[metric] ?? 0));
    }
    return Array.from(totals.entries())
      .map(([label, cost]) => ({ label, cost }))
      .sort((a, b) => b.cost - a.cost);
  }, [accountRows, dimension, metric]);

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return term ? grouped.filter((g) => g.label.toLowerCase().includes(term)) : grouped;
  }, [grouped, search]);

  const visibleTotal = visible.reduce((sum, g) => sum + g.cost, 0);
  const dimensionLabel = DIMENSIONS.find((d) => d.key === dimension)?.label ?? "";

  return (
    <div className="drilldown">
      <div className="drilldown-head">
        <div>
          <span className="drilldown-title">Account {accountId}</span>
          <span className="drilldown-sub">{accountRows.length} charge combination{accountRows.length === 1 ? "" : "s"}</span>
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
              <button key={m} className={m === metric ? "metric-pill active" : "metric-pill"} onClick={() => setMetric(m)}>
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
              onClick={() => setDimension(d.key)}
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
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Filter by ${dimensionLabel.toLowerCase()}...`}
          />
        </label>
        <span className="drilldown-total">
          {metricLabel(metric || "cost")} total: <strong>{formatMoney(visibleTotal)}</strong>
        </span>
      </div>

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
                {search ? "No matches for that search." : "No line items for this account."}
              </td>
            </tr>
          )}
          {visible.map((g) => (
            <tr key={g.label}>
              <td>{g.label}</td>
              <td>{formatMoney(g.cost)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
