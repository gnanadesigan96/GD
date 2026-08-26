import { Fragment, useState } from "react";
import { downloadCsv, formatBytes, metricLabel, toCsv } from "../lib/format";
import type { CurLoadResponse } from "../types";
import { AccountDrilldown } from "./AccountDrilldown";
import { BarChart } from "./BarChart";
import { DayDrilldown } from "./DayDrilldown";
import { LineChart } from "./LineChart";

const MAX_REPORT_ACCOUNTS = 10;

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
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [showPartFiles, setShowPartFiles] = useState(false);
  const [reportAccounts, setReportAccounts] = useState<Set<string>>(new Set());
  const [reportMetric, setReportMetric] = useState(data.available_cost_metrics[0] ?? "");
  // Falls back to the new dataset's first metric if a previously loaded
  // bill's selection doesn't exist in this one (e.g. this account has no
  // Reserved Instances, so no net_* metrics).
  const effectiveReportMetric = data.available_cost_metrics.includes(reportMetric)
    ? reportMetric
    : data.available_cost_metrics[0] ?? "";
  const hasDrilldown = data.drilldown.length > 0 && data.available_cost_metrics.length > 0;
  const hasDayDrilldown = data.day_drilldown.length > 0 && data.available_cost_metrics.length > 0;
  const hasPartFiles = data.part_files.length > 0;

  const toggleReportAccount = (accountId: string) => {
    setReportAccounts((prev) => {
      const next = new Set(prev);
      if (next.has(accountId)) {
        next.delete(accountId);
      } else if (next.size < MAX_REPORT_ACCOUNTS) {
        next.add(accountId);
      }
      return next;
    });
  };

  const downloadAccountReport = () => {
    const selected = new Set(reportAccounts);
    const rows = data.drilldown
      .filter((r) => selected.has(r.account_id))
      .map((r) => [r.account_id, r.product_category, r.resource_category, r.charge_type, (r.costs[effectiveReportMetric] ?? 0).toFixed(2)]);
    const csv = toCsv(
      ["Account ID", "Product Category", "Resource Category", "Charge Type", `${metricLabel(effectiveReportMetric)} (${data.currency || "USD"})`],
      rows,
    );
    downloadCsv(`cur-report-${data.billing_period}-${effectiveReportMetric}-${selected.size}accounts.csv`, csv);
  };

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
          {hasPartFiles ? (
            <button className="kpi-value kpi-value-button" onClick={() => setShowPartFiles((v) => !v)}>
              {data.part_file_count}
            </button>
          ) : (
            <span className="kpi-value">{data.part_file_count}</span>
          )}
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Load time</span>
          <span className="kpi-value">{(data.load_time_ms / 1000).toFixed(2)}s</span>
        </div>
      </div>

      {hasPartFiles && showPartFiles && (
        <div className="panel">
          <div className="drilldown-head">
            <span className="drilldown-title">Part files processed</span>
            <button className="drilldown-close" onClick={() => setShowPartFiles(false)} aria-label="Close part file list">
              Close
            </button>
          </div>
          <table className="drilldown-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Size</th>
              </tr>
            </thead>
            <tbody>
              {data.part_files.map((f) => (
                <tr key={f.key}>
                  <td title={f.key}>{f.key.split("/").pop()}</td>
                  <td>{formatBytes(f.size_bytes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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
        <h2>Cost by day</h2>
        {hasDayDrilldown && <p className="panel-hint">Click a day to see its cost broken down by product category, resource category, and charge type.</p>}
        <table className={hasDayDrilldown ? "account-table clickable" : "account-table"}>
          <thead>
            <tr>
              <th>Date</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {data.cost_by_day.map((d) => {
              const isSelected = d.date === selectedDay;
              return (
                <Fragment key={d.date}>
                  <tr
                    onClick={hasDayDrilldown ? () => setSelectedDay(isSelected ? null : d.date) : undefined}
                    className={isSelected ? "selected" : undefined}
                  >
                    <td>{d.date}</td>
                    <td>{money(d.cost)}</td>
                  </tr>
                  {hasDayDrilldown && isSelected && (
                    <tr className="drilldown-row">
                      <td colSpan={2} className="drilldown-cell">
                        <DayDrilldown
                          date={d.date}
                          rows={data.day_drilldown}
                          availableCostMetrics={data.available_cost_metrics}
                          formatMoney={money}
                          onClose={() => setSelectedDay(null)}
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

      <div className="panel">
        <h2>Cost by linked account</h2>
        {hasDrilldown && <p className="panel-hint">Click an account to see its cost broken down by product category, resource category, and charge type.</p>}

        {hasDrilldown && (
          <div className="report-toolbar">
            <label>
              Report cost metric
              <select value={effectiveReportMetric} onChange={(e) => setReportMetric(e.target.value)}>
                {data.available_cost_metrics.map((m) => (
                  <option key={m} value={m}>
                    {metricLabel(m)}
                  </option>
                ))}
              </select>
            </label>
            <span className="report-count">
              {reportAccounts.size} of {MAX_REPORT_ACCOUNTS} accounts selected
              {reportAccounts.size >= MAX_REPORT_ACCOUNTS ? " (maximum reached)" : ""}
            </span>
            <button className="report-download-button" disabled={reportAccounts.size === 0} onClick={downloadAccountReport}>
              Download report ({reportAccounts.size})
            </button>
          </div>
        )}

        <table className={hasDrilldown ? "account-table clickable" : "account-table"}>
          <thead>
            <tr>
              {hasDrilldown && <th className="report-checkbox-col"></th>}
              <th>Account ID</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {data.cost_by_account.map((a) => {
              const isSelected = a.account_id === selectedAccount;
              const isChecked = reportAccounts.has(a.account_id);
              return (
                <Fragment key={a.account_id}>
                  <tr
                    onClick={hasDrilldown ? () => setSelectedAccount(isSelected ? null : a.account_id) : undefined}
                    className={isSelected ? "selected" : undefined}
                  >
                    {hasDrilldown && (
                      <td className="report-checkbox-col" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          disabled={!isChecked && reportAccounts.size >= MAX_REPORT_ACCOUNTS}
                          onChange={() => toggleReportAccount(a.account_id)}
                        />
                      </td>
                    )}
                    <td>{a.account_id}</td>
                    <td>{money(a.cost)}</td>
                  </tr>
                  {hasDrilldown && isSelected && (
                    <tr className="drilldown-row">
                      <td colSpan={3} className="drilldown-cell">
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
