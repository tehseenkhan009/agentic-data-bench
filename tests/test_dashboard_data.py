"""Unit tests for the dashboard's pure parsing/aggregation module
(dashboard/backend/data.py) — empty-file handling, multi-run parsing, and
per-model aggregation correctness."""
from __future__ import annotations

import json
from pathlib import Path

from dashboard.backend.data import aggregate_by_model, load_benchmark_history, load_report, load_trace


def test_load_trace_missing_file_returns_empty_list(tmp_path: Path) -> None:
    assert load_trace(tmp_path / "does_not_exist.json") == []


def test_load_trace_parses_existing_file(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    entries = [{"agent": "Planner", "action": "plan", "timestamp": "2026-01-01T00:00:00+00:00"}]
    trace_path.write_text(json.dumps(entries), encoding="utf-8")

    assert load_trace(trace_path) == entries


def test_load_report_missing_file_returns_empty_string(tmp_path: Path) -> None:
    assert load_report(tmp_path / "does_not_exist.md") == ""


def test_load_report_parses_existing_file(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    report_path.write_text("# Analysis Report\n\nSome findings.", encoding="utf-8")

    assert load_report(report_path) == "# Analysis Report\n\nSome findings."


def test_load_benchmark_history_missing_file_returns_empty_list(tmp_path: Path) -> None:
    assert load_benchmark_history(tmp_path / "does_not_exist.jsonl") == []


def test_load_benchmark_history_parses_multiple_lines_and_skips_blanks(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    rows = [{"model": "gpt-4o-mini", "run_id": "a"}, {"model": "gpt-4o", "run_id": "b"}]
    history_path.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n\n",  # trailing blank line
        encoding="utf-8",
    )

    assert load_benchmark_history(history_path) == rows


def test_aggregate_by_model_empty_history_returns_empty_dict() -> None:
    assert aggregate_by_model([]) == {}


def test_aggregate_by_model_computes_per_model_stats() -> None:
    history = [
        {
            "model": "gpt-4o-mini", "success": True, "latency_seconds": 10.0,
            "estimated_cost_usd": 0.001, "n_retries_total": 1,
        },
        {
            "model": "gpt-4o-mini", "success": False, "latency_seconds": 20.0,
            "estimated_cost_usd": 0.002, "n_retries_total": 3,
        },
        {
            "model": "gpt-4o", "success": True, "latency_seconds": 2.0,
            "estimated_cost_usd": 0.01, "n_retries_total": 0,
        },
    ]

    summary = aggregate_by_model(history)

    assert set(summary.keys()) == {"gpt-4o-mini", "gpt-4o"}

    mini = summary["gpt-4o-mini"]
    assert mini["n_runs"] == 2
    assert mini["success_rate"] == 0.5
    assert mini["avg_latency_seconds"] == 15.0
    assert mini["avg_estimated_cost_usd"] == 0.0015
    assert mini["avg_retries"] == 2.0

    full = summary["gpt-4o"]
    assert full["n_runs"] == 1
    assert full["success_rate"] == 1.0
    assert full["avg_latency_seconds"] == 2.0
    assert full["avg_estimated_cost_usd"] == 0.01
    assert full["avg_retries"] == 0.0
