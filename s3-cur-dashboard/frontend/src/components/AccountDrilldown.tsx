import { useMemo } from "react";
import type { DrilldownRow } from "../types";
import { DrilldownPanel } from "./DrilldownPanel";

interface AccountDrilldownProps {
  accountId: string;
  rows: DrilldownRow[];
  availableCostMetrics: string[];
  formatMoney: (value: number) => string;
  onClose: () => void;
}

export function AccountDrilldown({ accountId, rows, availableCostMetrics, formatMoney, onClose }: AccountDrilldownProps) {
  const accountRows = useMemo(() => rows.filter((r) => r.account_id === accountId), [rows, accountId]);

  return (
    <DrilldownPanel
      title={`Account ${accountId}`}
      subtitle={`${accountRows.length} charge combination${accountRows.length === 1 ? "" : "s"}`}
      rows={accountRows}
      availableCostMetrics={availableCostMetrics}
      formatMoney={formatMoney}
      onClose={onClose}
    />
  );
}
