"""Unit tests for the benchmark harness's result-persistence helpers.

These test the pure file-writing logic (write_latest / append_history)
in isolation from run_single, which requires a real LLM call.
"""
from __future__ import annotations

import json
from pathlib import Path

from benchmarks.run_benchmark import BenchmarkResult, append_history, write_latest


def _make_result(model: str = "gpt-4o-mini", run_id: str = "run1") -> BenchmarkResult:
    return BenchmarkResult(
        model=model,
        success=True,
        halted_reason=None,
        n_retries_total=0,
        latency_seconds=1.23,
        prompt_tokens=100,
        completion_tokens=50,
        estimated_cost_usd=0.001,
        mentions_expected_category=True,
        run_id=run_id,
        timestamp="2026-01-01T00:00:00+00:00",
    )


def test_write_latest_overwrites(tmp_path: Path) -> None:
    out_dir = tmp_path / "results"
    write_latest([_make_result(run_id="run1")], out_dir)
    write_latest([_make_result(run_id="run2")], out_dir)

    latest = json.loads((out_dir / "latest_run.json").read_text(encoding="utf-8"))
    assert len(latest) == 1
    assert latest[0]["run_id"] == "run2"


def test_append_history_does_not_overwrite(tmp_path: Path) -> None:
    out_dir = tmp_path / "results"
    history_path = out_dir / "history.jsonl"

    append_history([_make_result(run_id="run1", model="gpt-4o-mini")], out_dir)
    append_history([_make_result(run_id="run2", model="gpt-4o")], out_dir)

    lines = history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    rows = [json.loads(line) for line in lines]
    assert rows[0]["run_id"] == "run1"
    assert rows[1]["run_id"] == "run2"
    assert rows[0]["model"] == "gpt-4o-mini"
    assert rows[1]["model"] == "gpt-4o"


def test_append_history_multiple_results_same_run(tmp_path: Path) -> None:
    out_dir = tmp_path / "results"
    results = [_make_result(model="gpt-4o-mini"), _make_result(model="gpt-4o")]
    append_history(results, out_dir)

    lines = (out_dir / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    for line in lines:
        row = json.loads(line)
        assert "run_id" in row and row["run_id"]
        assert "timestamp" in row and row["timestamp"]
