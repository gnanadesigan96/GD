import { metricLabel } from "../lib/format";

interface DayCostBreakdownProps {
  date: string;
  costs: Record<string, number>;
  availableCostMetrics: string[];
  formatMoney: (value: number) => string;
  onClose: () => void;
}

// Deliberately simple: just cost per metric (unblended/blended/net_*), no
// product/resource/charge-type dimension. That per-day category drill-down
// used to power this used the single largest grouping set in the backend's
// aggregate query -- dropping it measurably reduced peak memory on a large
// export. The account drill-down (see AccountDrilldown) still has the full
// category breakdown.
export function DayCostBreakdown({ date, costs, availableCostMetrics, formatMoney, onClose }: DayCostBreakdownProps) {
  return (
    <div className="drilldown">
      <div className="drilldown-head">
        <span className="drilldown-title">{date}</span>
        <button className="drilldown-close" onClick={onClose} aria-label="Close">
          Close
        </button>
      </div>
      <table className="drilldown-table">
        <thead>
          <tr>
            <th>Cost metric</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {availableCostMetrics.map((m) => (
            <tr key={m}>
              <td>{metricLabel(m)}</td>
              <td>{formatMoney(costs[m] ?? 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
