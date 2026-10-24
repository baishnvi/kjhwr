 import { useEffect, useState } from "react";
import { api } from "./api";
import { cutoffLabel, gwh, longDay, mw, pct, stamp } from "./format";
import DecisionChart from "./components/DecisionChart";
import { DailyChart, ErrorHistogram, HorizonChart, HourlyChart } from "./components/AccuracyCharts";

const CUTOFFS = [8, 9, 10, 11, 12];

function Figure({ label, value, note }) {
  return (
    <div className="figure">
      <div className="figure-label">{label}</div>
      <div className="figure-value">{value}</div>
      {note && <div className="figure-note">{note}</div>}
    </div>
  );
}

export default function App() {
  const [meta, setMeta] = useState(null);
  const [date, setDate] = useState("2026-01-14");
  const [cutoff, setCutoff] = useState(9);
  const [decision, setDecision] = useState(null);
  const [acc, setAcc] = useState(null);
  const [horizon, setHorizon] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.meta().then(setMeta).catch((e) => setError(e.message));
    api.horizon().then(setHorizon).catch(() => {});
  }, []);
  useEffect(() => {
    setError(null);
    api.decision(date, cutoff).then(setDecision).catch((e) => setError(e.message));
  }, [date, cutoff]);
  useEffect(() => { api.accuracy(cutoff).then(setAcc).catch(() => {}); }, [cutoff]);

  const m = decision?.metrics;
  const o = acc?.overall;
  const deliveryDate = decision?.deliveryDay;

  return (
    <div className="page">
      <header className="top">
        <div>
          <h1>Wind forecast monitor</h1>
          <p className="sub">GB national wind generation · day-ahead buying decisions, January 2026</p>
        </div>
        <div className="controls">
          <label>
            Decision date
            <input type="date" value={date} min={meta?.decisionFrom} max={meta?.decisionTo} onChange={(e) => e.target.value && setDate(e.target.value)} />
          </label>
          <label>
            Decision time (UK)
            <select value={cutoff} onChange={(e) => setCutoff(Number(e.target.value))}>
              {CUTOFFS.map((h) => <option key={h} value={h}>{cutoffLabel(h)}</option>)}
            </select>
          </label>
        </div>
      </header>

      {error && <div className="alert" role="alert">{error}</div>}

      <main>
        <section>
          <h2>What the forecast said when you had to decide</h2>
          {decision ? (
            <>
              <p className="lede">
                Buying on <b>{longDay(decision.decisionDay)}</b> for delivery on <b>{longDay(deliveryDate)}</b>, the latest wind forecast
                {" "}(made {stamp(decision.forecastPublishedRange?.[0])}) expected between <b>{mw(decision.minForecastMW)}</b> and <b>{mw(decision.peakForecastMW)}</b>.
                {decision.bufferP90MW != null && <> In 9 of 10 past half-hours the wind came in no more than <b>{mw(Math.max(0, decision.bufferP90MW))}</b> below this kind of forecast, so plan to cover up to that much extra with thermal or other supply.</>}
              </p>
              <DecisionChart points={decision.points} />
              <div className="figures">
                <Figure label="Forecast energy" value={gwh(decision.forecastMWh)} note="for the whole delivery day" />
                <Figure label="Actual energy" value={gwh(decision.actualMWh)} note="what the wind really produced" />
                <Figure label="Average error that day" value={mw(m?.mae)} note={m ? `${pct(m.nmae)} of average output` : null} />
                <Figure label="Bias that day" value={m ? `${m.bias > 0 ? "+" : ""}${Math.round(m.bias).toLocaleString("en-GB")} MW` : "–"}
                        note={m ? (m.bias > 0 ? "forecast too high → shortfall to buy" : "forecast too low → over-bought") : null} />
              </div>
            </>
          ) : <p className="muted">Loading…</p>}
        </section>

        <section>
          <h2>How reliable has the forecast been in January?</h2>
          <p className="lede">
            Every half-hour of every January delivery day, comparing the forecast available at {cutoffLabel(cutoff)} the day before with what was generated.
          </p>
          {o ? (
            <div className="figures">
              <Figure label="Average error (MAE)" value={mw(o.mae)} note={`${pct(o.nmae)} of average output`} />
              <Figure label="Typical swing (RMSE)" value={mw(o.rmse)} note="penalises large misses" />
              <Figure label="90th percentile error" value={mw(o.p90_abs)} note="1 in 10 half-hours is worse than this" />
              <Figure label="Average bias" value={`${o.bias > 0 ? "+" : ""}${Math.round(o.bias).toLocaleString("en-GB")} MW`} note={o.bias > 0 ? "tends to over-forecast" : "tends to under-forecast"} />
            </div>
          ) : <p className="muted">Loading…</p>}

          <div className="grid">
            <div>
              <h3>Error by delivery day</h3>
              <p className="cap">Click a bar to open that decision.</p>
              {acc && <DailyChart daily={acc.daily} selected={deliveryDate} onSelect={(d) => {
                const prev = new Date(d + "T00:00:00Z"); prev.setUTCDate(prev.getUTCDate() - 1);
                setDate(prev.toISOString().slice(0, 10));
              }} />}
            </div>
            <div>
              <h3>Error by how far ahead it was made</h3>
              <p className="cap">All forecasts published in January, grouped by hours before delivery.</p>
              {horizon && <HorizonChart horizon={horizon} />}
            </div>
            <div>
              <h3>Error by time of day</h3>
              <p className="cap">Average error at each hour of the delivery day.</p>
              {acc && <HourlyChart hourly={acc.hourly} />}
            </div>
            <div>
              <h3>Distribution of errors</h3>
              <p className="cap">Orange: forecast too high (shortfall). Teal: forecast too low.</p>
              {acc && <ErrorHistogram histogram={acc.histogram} />}
            </div>
          </div>
        </section>
      </main>

      <footer>
        Data: Elexon BMRS FUELHH (actual wind) and WINDFOR (wind forecasts). Error = forecast − actual. Times are UK local time (GMT in January).
        {meta?.source && <> Source in use: {meta.source}.</>}
      </footer>
    </div>
  );
}