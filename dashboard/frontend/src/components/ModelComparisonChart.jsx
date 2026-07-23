import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { buildModelColorMap } from "../lib/modelColors";

// One measure per chart (never a dual-axis chart) — latency and cost are
// different scales, so they get their own single-axis bar chart each.
function buildBarData(summary, key) {
  return Object.entries(summary).map(([model, stats]) => ({ model, value: stats[key] }));
}

// Pivots the flat history rows into one point per benchmark run (grouped by
// run_id, since every model in a run finishes within moments of each other),
// with one column per model — the shape Recharts' multi-line chart wants.
function buildTrendData(history, metricKey) {
  const byRun = new Map();
  for (const row of history) {
    if (!byRun.has(row.run_id)) {
      byRun.set(row.run_id, { run_id: row.run_id, timestamp: row.timestamp });
    }
    const point = byRun.get(row.run_id);
    point[row.model] = row[metricKey];
    if (row.timestamp < point.timestamp) point.timestamp = row.timestamp;
  }
  return [...byRun.values()].sort((a, b) => (a.timestamp > b.timestamp ? 1 : -1));
}

function formatRunLabel(ts) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function BarComparison({ title, data, colorMap, valueFormatter }) {
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis dataKey="model" tick={{ fill: "var(--text-muted)", fontSize: 12 }} axisLine={{ stroke: "var(--baseline)" }} tickLine={false} />
          <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} axisLine={{ stroke: "var(--baseline)" }} tickLine={false} width={48} />
          <Tooltip
            contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13 }}
            formatter={valueFormatter}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={64}>
            {data.map((entry) => (
              <Cell key={entry.model} fill={colorMap[entry.model]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function TrendLine({ title, data, models, colorMap, valueFormatter }) {
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatRunLabel}
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--baseline)" }}
            tickLine={false}
          />
          <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} axisLine={{ stroke: "var(--baseline)" }} tickLine={false} width={48} />
          <Tooltip
            labelFormatter={formatRunLabel}
            contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13 }}
            formatter={valueFormatter}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {models.map((model) => (
            <Line
              key={model}
              type="monotone"
              dataKey={model}
              stroke={colorMap[model]}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function ModelComparisonChart({ history, summary }) {
  const models = useMemo(() => Object.keys(summary), [summary]);
  const colorMap = useMemo(() => buildModelColorMap(models), [models]);

  const latencyBarData = useMemo(() => buildBarData(summary, "avg_latency_seconds"), [summary]);
  const costBarData = useMemo(() => buildBarData(summary, "avg_estimated_cost_usd"), [summary]);
  const latencyTrend = useMemo(() => buildTrendData(history, "latency_seconds"), [history]);
  const costTrend = useMemo(() => buildTrendData(history, "estimated_cost_usd"), [history]);

  if (models.length === 0) return null;

  return (
    <>
      <div className="chart-grid">
        <BarComparison
          title="Avg latency by model (s)"
          data={latencyBarData}
          colorMap={colorMap}
          valueFormatter={(v) => `${v.toFixed(2)}s`}
        />
        <BarComparison
          title="Avg estimated cost by model ($)"
          data={costBarData}
          colorMap={colorMap}
          valueFormatter={(v) => `$${v.toFixed(6)}`}
        />
      </div>
      <div className="chart-grid">
        <TrendLine
          title="Latency per run over time (s)"
          data={latencyTrend}
          models={models}
          colorMap={colorMap}
          valueFormatter={(v) => `${Number(v).toFixed(2)}s`}
        />
        <TrendLine
          title="Estimated cost per run over time ($)"
          data={costTrend}
          models={models}
          colorMap={colorMap}
          valueFormatter={(v) => `$${Number(v).toFixed(6)}`}
        />
      </div>
    </>
  );
}
