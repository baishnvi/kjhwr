async function get(path) {
  const r = await fetch(path);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch { /* ignore */ }
    throw new Error(msg);
  }
  return r.json();
}

export const api = {
  meta: () => get("/api/meta"),
  decision: (date, cutoff) => get(`/api/decision?date=${date}&cutoff=${cutoff}`),
  accuracy: (cutoff) => get(`/api/accuracy?cutoff=${cutoff}`),
  horizon: () => get("/api/horizon?bucket=6"),
};
