import { useMemo } from "react";
import type { DayDrilldownRow } from "../types";
import { DrilldownPanel } from "./DrilldownPanel";

interface DayDrilldownProps {
  date: string;
  rows: DayDrilldownRow[];
  availableCostMetrics: string[];
  formatMoney: (value: number) => string;
  onClose: () => void;
}

export function DayDrilldown({ date, rows, availableCostMetrics, formatMoney, onClose }: DayDrilldownProps) {
  const dayRows = useMemo(() => rows.filter((r) => r.date === date), [rows, date]);

  return (
    <DrilldownPanel
      title={date}
      subtitle={`${dayRows.length} charge combination${dayRows.length === 1 ? "" : "s"}`}
      rows={dayRows}
      availableCostMetrics={availableCostMetrics}
      formatMoney={formatMoney}
      onClose={onClose}
    />
  );
}
