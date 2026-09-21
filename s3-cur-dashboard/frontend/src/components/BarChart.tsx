interface BarChartProps {
  data: { label: string; value: number }[];
  formatValue: (value: number) => string;
}

export function BarChart({ data, formatValue }: BarChartProps) {
  const top = data.slice(0, 10);
  const max = Math.max(1, ...top.map((d) => d.value));

  return (
    <div className="bar-chart">
      {top.map((d) => (
        <div className="bar-row" key={d.label}>
          <span className="bar-label" title={d.label}>
            {d.label}
          </span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(d.value / max) * 100}%` }} />
          </div>
          <span className="bar-value">{formatValue(d.value)}</span>
        </div>
      ))}
    </div>
  );
}
