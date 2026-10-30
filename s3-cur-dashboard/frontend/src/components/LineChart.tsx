interface LineChartProps {
  data: { date: string; cost: number }[];
}

const WIDTH = 640;
const HEIGHT = 200;
const PADDING = 24;

export function LineChart({ data }: LineChartProps) {
  if (data.length === 0) {
    return <p className="empty">No daily data</p>;
  }

  const max = Math.max(1, ...data.map((d) => d.cost));
  const stepX = data.length > 1 ? (WIDTH - PADDING * 2) / (data.length - 1) : 0;

  const points = data.map((d, i) => {
    const x = PADDING + i * stepX;
    const y = HEIGHT - PADDING - (d.cost / max) * (HEIGHT - PADDING * 2);
    return `${x},${y}`;
  });

  const areaPoints = `${PADDING},${HEIGHT - PADDING} ${points.join(" ")} ${WIDTH - PADDING},${HEIGHT - PADDING}`;

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="line-chart" role="img" aria-label="Daily cost trend">
      <polyline points={areaPoints} className="line-area" />
      <polyline points={points.join(" ")} className="line-stroke" />
      {data.length <= 31 &&
        points.map((p, i) => {
          const [x, y] = p.split(",");
          return <circle key={data[i].date} cx={x} cy={y} r={2.5} className="line-dot" />;
        })}
      <text x={PADDING} y={HEIGHT - 6} className="axis-label">
        {data[0].date}
      </text>
      <text x={WIDTH - PADDING} y={HEIGHT - 6} textAnchor="end" className="axis-label">
        {data[data.length - 1].date}
      </text>
    </svg>
  );
}
