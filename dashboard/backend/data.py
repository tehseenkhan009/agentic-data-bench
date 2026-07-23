"""Pure parsing/aggregation functions for the observability dashboard.

No FastAPI/HTTP imports here on purpose — this module only reads the flat
JSON/JSONL files that are already the source of truth for the rest of the
repo (`outputs/trace.json`, `benchmarks/results/history.jsonl`), so it can be
unit tested the same way `src/skills/` is (see docs/GOVERNANCE.md section 3).
"""
from __future__ import annotations

import json
from pathlib import Path


def load_trace(trace_path: Path) -> list[dict]:
    """Return the parsed trace entries for a single pipeline run, or an
    empty list if the run hasn't happened yet."""
    if not trace_path.exists():
        return []
    return json.loads(trace_path.read_text(encoding="utf-8"))


def load_benchmark_history(history_path: Path) -> list[dict]:
    """Return every benchmark result ever appended to history.jsonl, or an
    empty list if no benchmark has been run yet. Blank lines are skipped."""
    if not history_path.exists():
        return []
    rows = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def aggregate_by_model(history: list[dict]) -> dict[str, dict]:
    """Per-model KPI summary across all historical benchmark runs: success
    rate, average latency, average estimated cost, average retries."""
    by_model: dict[str, list[dict]] = {}
    for row in history:
        by_model.setdefault(row["model"], []).append(row)

    summary: dict[str, dict] = {}
    for model, rows in by_model.items():
        n = len(rows)
        successes = sum(1 for r in rows if r.get("success"))
        summary[model] = {
            "n_runs": n,
            "success_rate": round(successes / n, 4),
            "avg_latency_seconds": round(sum(r.get("latency_seconds", 0) for r in rows) / n, 4),
            "avg_estimated_cost_usd": round(sum(r.get("estimated_cost_usd", 0) for r in rows) / n, 6),
            "avg_retries": round(sum(r.get("n_retries_total", 0) for r in rows) / n, 4),
        }
    return summary
