export const mw = (v) => (v == null ? "–" : `${Math.round(v).toLocaleString("en-GB")} MW`);
export const gwh = (v) => (v == null ? "–" : `${(v / 1000).toFixed(1)} GWh`);
export const pct = (v) => (v == null ? "–" : `${v.toFixed(1)}%`);
export const hhmm = (iso) => iso.slice(11, 16);
export const longDay = (d) =>
  new Date(d + "T00:00:00Z").toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "long", timeZone: "UTC" });
export const shortDay = (d) =>
  new Date(d + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
export const stamp = (iso) =>
  iso ? `${shortDay(iso.slice(0, 10))} ${hhmm(iso)}` : "–";
export const cutoffLabel = (h) => `${String(Math.floor(h)).padStart(2, "0")}:${h % 1 ? "30" : "00"}`;
