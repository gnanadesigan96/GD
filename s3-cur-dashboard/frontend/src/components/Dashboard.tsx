import { Fragment, useState } from "react";
import type { CurLoadResponse } from "../types";
import { AccountDrilldown } from "./AccountDrilldown";
import { BarChart } from "./BarChart";
import { LineChart } from "./LineChart";

interface DashboardProps {
  data: CurLoadResponse;
}

function formatMoney(value: number, currency: string | null): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return value.toFixed(2);
  }
}

export function Dashboard({ data }: DashboardProps) {
  const money = (v: number) => formatMoney(v, data.currency);
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const hasDrilldown = data.drilldown.length > 0 && data.available_cost_metrics.length > 0;

  return (
    <div className="dashboard">
      <div className="kpi-row">
        <div className="kpi-card">
          <span className="kpi-label">Total cost — {data.billing_period}</span>
          <span className="kpi-value">{money(data.total_cost)}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Source format</span>
          <span className="kpi-value">{data.file_format === "parquet" ? "Parquet" : "CSV (gzip)"}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Part files scanned</span>
          <span className="kpi-value">{data.part_file_count}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Load time</span>
          <span className="kpi-value">{(data.load_time_ms / 1000).toFixed(2)}s</span>
        </div>
      </div>

      <div className="panel">
        <h2>Cost by service</h2>
        <BarChart
          data={data.cost_by_service.map((s) => ({ label: s.service, value: s.cost }))}
          formatValue={money}
        />
      </div>

      <div className="panel">
        <h2>Daily cost trend</h2>
        <LineChart data={data.cost_by_day} />
      </div>

      <div className="panel">
        <h2>Cost by linked account</h2>
        {hasDrilldown && <p className="panel-hint">Click an account to see its cost broken down by product category, resource category, and charge type.</p>}
        <table className={hasDrilldown ? "account-table clickable" : "account-table"}>
          <thead>
            <tr>
              <th>Account ID</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {data.cost_by_account.map((a) => {
              const isSelected = a.account_id === selectedAccount;
              return (
                <Fragment key={a.account_id}>
                  <tr
                    onClick={hasDrilldown ? () => setSelectedAccount(isSelected ? null : a.account_id) : undefined}
                    className={isSelected ? "selected" : undefined}
                  >
                    <td>{a.account_id}</td>
                    <td>{money(a.cost)}</td>
                  </tr>
                  {hasDrilldown && isSelected && (
                    <tr className="drilldown-row">
                      <td colSpan={2} className="drilldown-cell">
                        <AccountDrilldown
                          accountId={a.account_id}
                          rows={data.drilldown}
                          availableCostMetrics={data.available_cost_metrics}
                          formatMoney={money}
                          onClose={() => setSelectedAccount(null)}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
