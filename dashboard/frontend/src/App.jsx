import { useCallback, useEffect, useState } from "react";
import "./App.css";
import TraceTimeline from "./components/TraceTimeline";
import BenchmarkSummary from "./components/BenchmarkSummary";

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} returned ${res.status}`);
  return res.json();
}

export default function App() {
  const [tab, setTab] = useState("trace");
  const [trace, setTrace] = useState([]);
  const [history, setHistory] = useState([]);
  const [summary, setSummary] = useState({});
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [traceData, benchmarkData] = await Promise.all([
        fetchJson("/api/trace"),
        fetchJson("/api/benchmark-history"),
      ]);
      setTrace(traceData.trace ?? []);
      setHistory(benchmarkData.history ?? []);
      setSummary(benchmarkData.summary ?? {});
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>AgentBench Observability Dashboard</h1>
          <p>Visualizes the multi-agent trace and benchmark history produced by the AgentBench pipeline.</p>
        </div>
        <button type="button" className="refresh-button" onClick={load} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className="tabs">
        <button
          type="button"
          className={`tab-button ${tab === "trace" ? "active" : ""}`}
          onClick={() => setTab("trace")}
        >
          Trace Timeline
        </button>
        <button
          type="button"
          className={`tab-button ${tab === "benchmark" ? "active" : ""}`}
          onClick={() => setTab("benchmark")}
        >
          Benchmark History
        </button>
      </div>

      <div className="panel">
        {error ? (
          <div className="error-state">
            Could not reach the dashboard backend at <code>/api</code>: {error}. Is{" "}
            <code>uvicorn dashboard.backend.main:app</code> running?
          </div>
        ) : tab === "trace" ? (
          <TraceTimeline trace={trace} />
        ) : (
          <BenchmarkSummary history={history} summary={summary} />
        )}
      </div>
    </div>
  );
}
