import { useMemo, useState } from "react";
import type { DrilldownRow } from "../types";

interface AccountDrilldownProps {
  accountId: string;
  rows: DrilldownRow[];
  availableCostMetrics: string[];
  formatMoney: (value: number) => string;
  onClose: () => void;
}

function metricLabel(metric: string): string {
  // "net_unblended_cost" -> "Net Unblended Cost"
  return metric
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function AccountDrilldown({ accountId, rows, availableCostMetrics, formatMoney, onClose }: AccountDrilldownProps) {
  const [metric, setMetric] = useState(availableCostMetrics[0] ?? "");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const accountRows = useMemo(() => rows.filter((r) => r.account_id === accountId), [rows, accountId]);

  const categories = useMemo(
    () => Array.from(new Set(accountRows.map((r) => r.product_category))).sort(),
    [accountRows]
  );

  const visibleRows = useMemo(() => {
    const filtered = categoryFilter ? accountRows.filter((r) => r.product_category === categoryFilter) : accountRows;
    return [...filtered].sort((a, b) => (b.costs[metric] ?? 0) - (a.costs[metric] ?? 0));
  }, [accountRows, categoryFilter, metric]);

  const total = visibleRows.reduce((sum, r) => sum + (r.costs[metric] ?? 0), 0);

  return (
    <div className="drilldown">
      <div className="drilldown-head">
        <div>
          <span className="drilldown-title">Account {accountId}</span>
          <span className="drilldown-sub">{visibleRows.length} charge combination{visibleRows.length === 1 ? "" : "s"}</span>
        </div>
        <button className="drilldown-close" onClick={onClose} aria-label="Close drill-down">
          Close
        </button>
      </div>

      {availableCostMetrics.length > 0 && (
        <div className="drilldown-metrics">
          {availableCostMetrics.map((m) => (
            <button
              key={m}
              className={m === metric ? "metric-pill active" : "metric-pill"}
              onClick={() => setMetric(m)}
            >
              {metricLabel(m)}
            </button>
          ))}
        </div>
      )}

      <div className="drilldown-filter">
        <label>
          Product category
          <select value={categoryFilter ?? ""} onChange={(e) => setCategoryFilter(e.target.value || null)}>
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <span className="drilldown-total">
          {metric ? metricLabel(metric) : "Cost"} total: <strong>{formatMoney(total)}</strong>
        </span>
      </div>

      <table className="drilldown-table">
        <thead>
          <tr>
            <th>Product category</th>
            <th>Resource category</th>
            <th>Charge type</th>
            <th>{metric ? metricLabel(metric) : "Cost"}</th>
          </tr>
        </thead>
        <tbody>
          {visibleRows.length === 0 && (
            <tr>
              <td colSpan={4} className="empty">
                No line items for this account.
              </td>
            </tr>
          )}
          {visibleRows.map((r, i) => (
            <tr key={`${r.product_category}-${r.resource_category}-${r.charge_type}-${i}`}>
              <td>{r.product_category}</td>
              <td>{r.resource_category}</td>
              <td>{r.charge_type}</td>
              <td>{formatMoney(r.costs[metric] ?? 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
