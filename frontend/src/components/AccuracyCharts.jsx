import { Bar, BarChart, CartesianGrid, Cell, Line, ComposedChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from "recharts";
import { mw, shortDay } from "../format";

const axis = { tickLine: false, stroke: "var(--muted)" };
const yAxis = (label) => (
  <YAxis tickLine={false} axisLine={false} stroke="var(--muted)" width={44} tickFormatter={(v) => `${v / 1000}k`}
         label={{ value: label, position: "insideTopLeft", offset: 0, fill: "var(--muted)" }} />
);
const fmt = (v) => (typeof v === "number" ? mw(v) : v);

export function DailyChart({ daily, selected, onSelect }) {
  const data = daily.filter((d) => d.n).map((d) => ({ ...d, label: shortDay(d.date) }));
  return (
    <div className="chart">
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
                       onClick={(e) => e?.activePayload && onSelect(e.activePayload[0].payload.date)}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" interval={3} {...axis} />
          {yAxis("MW")}
          <Tooltip formatter={fmt} />
          <Bar dataKey="mae" name="Average error (MAE)" radius={[2, 2, 0, 0]}>
            {data.map((d) => <Cell key={d.date} fill={d.date === selected ? "var(--forecast)" : "var(--bar)"} />)}
          </Bar>
          <Line dataKey="p90_abs" name="90th percentile error" stroke="var(--warn)" strokeWidth={2} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HorizonChart({ horizon }) {
  return (
    <div className="chart">
      <ResponsiveContainer>
        <ComposedChart data={horizon} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" {...axis} />
          {yAxis("MW")}
          <Tooltip formatter={fmt} />
          <Bar dataKey="mae" name="Average error (MAE)" fill="var(--bar)" radius={[2, 2, 0, 0]} />
          <Line dataKey="p90_abs" name="90th percentile error" stroke="var(--warn)" strokeWidth={2} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HourlyChart({ hourly }) {
  const data = hourly.filter((h) => h.n).map((h) => ({ ...h, label: `${String(h.hour).padStart(2, "0")}:00` }));
  return (
    <div className="chart">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" interval={3} {...axis} />
          {yAxis("MW")}
          <Tooltip formatter={fmt} />
          <Bar dataKey="mae" name="Average error (MAE)" fill="var(--bar)" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ErrorHistogram({ histogram }) {
  const data = histogram.map((b) => ({ ...b, label: `${b.from}`, mid: b.from + 250 }));
  return (
    <div className="chart">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" interval={Math.ceil(data.length / 8)} {...axis} tickFormatter={(v) => `${v / 1000}k`} />
          <YAxis tickLine={false} axisLine={false} stroke="var(--muted)" width={36} />
          <Tooltip formatter={(v) => [`${v} half-hours`, "Count"]} labelFormatter={(l) => `Error from ${l} MW`} />
          <ReferenceLine x="0" stroke="var(--ink)" />
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {data.map((b) => <Cell key={b.from} fill={b.from >= 0 ? "var(--warn)" : "var(--forecast)"} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
