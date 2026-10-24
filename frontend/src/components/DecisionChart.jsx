import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { hhmm, mw } from "../format";

function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="tip">
      <b>{label}</b>
      <div>Forecast: {mw(p.forecast)}</div>
      <div>Actual: {mw(p.actual)}</div>
      {p.low != null && <div>Likely range: {mw(p.low)} to {mw(p.high)}</div>}
      {p.published && <div className="muted">Forecast made {p.published.slice(5, 10)} {hhmm(p.published)}</div>}
    </div>
  );
}

export default function DecisionChart({ points }) {
  const data = points.map((p) => ({
    ...p,
    label: hhmm(p.t),
    band: p.low != null ? [p.low, p.high] : null,
  }));
  return (
    <div className="chart tall" role="img" aria-label="Forecast versus actual wind generation for the delivery day">
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" interval={5} tickLine={false} stroke="var(--muted)" />
          <YAxis tickFormatter={(v) => `${v / 1000}k`} tickLine={false} axisLine={false} stroke="var(--muted)" width={44}
                 label={{ value: "MW", position: "insideTopLeft", offset: 0, fill: "var(--muted)" }} />
          <Tooltip content={<Tip />} />
          <Legend verticalAlign="top" align="right" iconType="plainline" height={28} />
          <Area dataKey="band" name="Likely range (P10–P90 of past errors)" stroke="none" fill="var(--band)" fillOpacity={0.55} connectNulls isAnimationActive={false} />
          <Line dataKey="forecast" name="Forecast at decision time" stroke="var(--forecast)" strokeWidth={2.5} dot={false} connectNulls isAnimationActive={false} />
          <Line dataKey="actual" name="Actual generation" stroke="var(--ink)" strokeWidth={2} strokeDasharray="5 3" dot={false} connectNulls isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
