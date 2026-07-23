import { groupTrace } from "../lib/groupTrace";

function formatTime(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleTimeString();
}

function SingleEntry({ entry }) {
  return (
    <div className="trace-card">
      <div className="trace-card-header">
        <span className="agent-badge">{entry.agent}</span>
        <span className="trace-action">{entry.action}</span>
        <span className="trace-timestamp">{formatTime(entry.timestamp)}</span>
      </div>
      <div className="trace-body">
        {Array.isArray(entry.steps) && entry.steps.length > 0 && (
          <ol>
            {entry.steps.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ol>
        )}
        {entry.halted && (
          <p style={{ color: "var(--status-critical)" }}>
            Run halted: the Planner could not answer this question from the given dataset.
          </p>
        )}
        {entry.agent === "Reporter" && (
          <p className="trace-action">Report written ({entry.length} characters).</p>
        )}
        {entry.usage && (
          <p className="trace-action">
            tokens: {entry.usage.prompt_tokens ?? 0} in / {entry.usage.completion_tokens ?? 0} out
          </p>
        )}
      </div>
    </div>
  );
}

function Attempt({ attempt, index }) {
  const passed = attempt.reviewer ? attempt.reviewer.passed : attempt.analyst.success;
  const findings = attempt.reviewer?.findings ?? [];

  return (
    <div className={`attempt ${passed ? "pass" : "fail"}`}>
      <div className="attempt-header">
        <span>Attempt {index + 1}</span>
        <span className={`status-pill ${passed ? "pass" : "fail"}`}>{passed ? "Passed" : "Failed"}</span>
        <span className="trace-timestamp">{formatTime(attempt.analyst.timestamp)}</span>
      </div>
      <div className="trace-body">
        <pre>{attempt.analyst.code}</pre>
        {attempt.analyst.error && <p style={{ color: "var(--status-critical)" }}>{attempt.analyst.error}</p>}
        {findings.length > 0 && (
          <ul className="findings">
            {findings.map((finding, idx) => (
              <li key={idx}>{finding}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function StepGroup({ group }) {
  return (
    <div className="step-group">
      <div className="step-group-title">
        {group.step}
        {group.attempts.length > 1 && (
          <span className="trace-action"> — {group.attempts.length} attempts</span>
        )}
      </div>
      {group.attempts.map((attempt, idx) => (
        <Attempt key={idx} attempt={attempt} index={idx} />
      ))}
    </div>
  );
}

export default function TraceTimeline({ trace }) {
  if (!trace || trace.length === 0) {
    return (
      <div className="empty-state">
        <p>No run trace found yet. Run the pipeline once to generate one:</p>
        <code>python main.py --data data/sample_sales.csv --question "..."</code>
      </div>
    );
  }

  const groups = groupTrace(trace);

  return (
    <div className="trace-list">
      {groups.map((group, idx) =>
        group.type === "single" ? (
          <SingleEntry key={idx} entry={group.entry} />
        ) : (
          <StepGroup key={idx} group={group} />
        ),
      )}
    </div>
  );
}
