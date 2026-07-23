import { useMemo, useState } from "react";
import { buildModelColorMap } from "../lib/modelColors";
import ModelComparisonChart from "./ModelComparisonChart";

function ModelSwatch({ color }) {
  return <span className="model-swatch" style={{ background: color }} />;
}

export default function BenchmarkSummary({ history, summary }) {
  const models = useMemo(() => Object.keys(summary), [summary]);
  const colorMap = useMemo(() => buildModelColorMap(models), [models]);
  const [modelFilter, setModelFilter] = useState("all");

  if (!history || history.length === 0) {
    return (
      <div className="empty-state">
        <p>No benchmark history found yet. Run the benchmark harness once to generate one:</p>
        <code>python benchmarks/run_benchmark.py</code>
      </div>
    );
  }

  const rows = (modelFilter === "all" ? history : history.filter((r) => r.model === modelFilter))
    .slice()
    .sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));

  return (
    <>
      <div className="kpi-grid">
        {models.map((model) => {
          const s = summary[model];
          return (
            <div className="kpi-card" key={model}>
              <div className="kpi-card-model">
                <ModelSwatch color={colorMap[model]} />
                {model}
              </div>
              <div className="kpi-row">
                <span>Success rate</span>
                <strong>{Math.round(s.success_rate * 100)}%</strong>
              </div>
              <div className="kpi-row">
                <span>Avg latency</span>
                <strong>{s.avg_latency_seconds.toFixed(2)}s</strong>
              </div>
              <div className="kpi-row">
                <span>Avg cost</span>
                <strong>${s.avg_estimated_cost_usd.toFixed(6)}</strong>
              </div>
              <div className="kpi-row">
                <span>Avg retries</span>
                <strong>{s.avg_retries.toFixed(1)}</strong>
              </div>
              <div className="kpi-row">
                <span>Runs</span>
                <strong>{s.n_runs}</strong>
              </div>
            </div>
          );
        })}
      </div>

      <ModelComparisonChart history={history} summary={summary} />

      <div className="runs-table-header">
        <h3>All runs</h3>
        <select value={modelFilter} onChange={(e) => setModelFilter(e.target.value)}>
          <option value="all">All models</option>
          {models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </div>
      <div className="table-scroll">
        <table className="runs-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Model</th>
              <th>Result</th>
              <th>Retries</th>
              <th>Latency (s)</th>
              <th>Cost ($)</th>
              <th>Run ID</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={`${row.run_id}-${row.model}-${idx}`}>
                <td>{new Date(row.timestamp).toLocaleString()}</td>
                <td>
                  <ModelSwatch color={colorMap[row.model]} /> {row.model}
                </td>
                <td style={{ color: row.success ? "var(--status-good)" : "var(--status-critical)" }}>
                  {row.success ? "Pass" : "Fail"}
                </td>
                <td>{row.n_retries_total}</td>
                <td>{row.latency_seconds}</td>
                <td>{row.estimated_cost_usd}</td>
                <td>{row.run_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
