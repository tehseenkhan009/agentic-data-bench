"""
Benchmark harness: runs the same task across multiple model configurations and
scores each on correctness, guardrail pass rate, latency, and estimated cost.

This directly implements the job requirement to "experimentally evaluate,
benchmark, and validate AI models, agents, and workflow variants ... focusing
on achieving the best possible results with minimal resource expenditure."

Usage:
    python benchmarks/run_benchmark.py
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.graph import build_graph, initial_state
from src.llm_providers import get_llm

# Rough public per-1M-token pricing snapshot (USD) used only for *relative*
# cost comparison in this demo — update before relying on absolute numbers.
# Free-tier/preview models (Gemini free tier, NVIDIA NIM preview) are $0 while
# that pricing holds; swap in paid-tier rates once that changes.
MODEL_PRICING_PER_1M = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gemini-flash-lite-latest": {"input": 0.0, "output": 0.0},  # Google AI Studio free tier
    "meta/llama-3.3-70b-instruct": {"input": 0.0, "output": 0.0},  # NVIDIA NIM free/preview tier
}

BENCHMARK_TASK = {
    "data": "data/sample_sales.csv",
    "question": (
        "Which product category has the strongest revenue growth trend, and is it "
        "statistically robust or driven by outliers?"
    ),
    # Ground-truth-ish expectation for a crude correctness check in this demo:
    # Electronics grows steadily; Toys has an April outlier spike that should be
    # flagged, not reported as a genuine trend.
    "expected_category_mentioned": "Electronics",
}

MODEL_CONFIGS = ["gpt-4o-mini", "gpt-4.1", "gemini-flash-lite-latest", "meta/llama-3.3-70b-instruct"]


@dataclass
class BenchmarkResult:
    model: str
    success: bool
    halted_reason: str | None
    n_retries_total: int
    latency_seconds: float
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    mentions_expected_category: bool
    run_id: str
    timestamp: str


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING_PER_1M.get(model)
    if not pricing:
        return float("nan")
    return (prompt_tokens / 1_000_000) * pricing["input"] + (completion_tokens / 1_000_000) * pricing["output"]


def run_single(model: str, df: pd.DataFrame, question: str, run_id: str) -> BenchmarkResult:
    llm = get_llm(model, temperature=0)
    app = build_graph(llm)
    state = initial_state(question, df)

    start = time.perf_counter()
    final_state = app.invoke(state)
    latency = time.perf_counter() - start

    n_retries = sum(1 for entry in final_state["trace"] if entry.get("action") == "review" and not entry.get("passed", True))
    report_text = final_state.get("report", "")
    mentions = BENCHMARK_TASK["expected_category_mentioned"].lower() in report_text.lower()

    prompt_tokens = sum(entry.get("usage", {}).get("prompt_tokens", 0) for entry in final_state["trace"])
    completion_tokens = sum(entry.get("usage", {}).get("completion_tokens", 0) for entry in final_state["trace"])

    return BenchmarkResult(
        model=model,
        success=not bool(final_state.get("halted_reason")),
        halted_reason=final_state.get("halted_reason"),
        n_retries_total=n_retries,
        latency_seconds=round(latency, 2),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost_usd=round(_estimate_cost(model, prompt_tokens, completion_tokens), 6),
        mentions_expected_category=mentions,
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def write_latest(results: list[BenchmarkResult], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest_run.json"
    out_path.write_text(json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8")
    return out_path


def append_history(results: list[BenchmarkResult], out_dir: Path) -> Path:
    """Append each result as one JSON line to history.jsonl (never overwritten),
    so the dashboard can show trends across benchmark runs over time."""
    out_dir.mkdir(parents=True, exist_ok=True)
    history_path = out_dir / "history.jsonl"
    with history_path.open("a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(asdict(r)) + "\n")
    return history_path


def main() -> None:
    load_dotenv()
    df = pd.read_csv(BENCHMARK_TASK["data"])
    run_id = uuid.uuid4().hex[:8]

    results = []
    for model in MODEL_CONFIGS:
        print(f"Running benchmark for model={model} ...")
        try:
            result = run_single(model, df, BENCHMARK_TASK["question"], run_id)
        except Exception as e:  # noqa: BLE001 - one provider's outage/rate-limit shouldn't
            # crash the whole benchmark run or lose results already computed for
            # other models (nothing is persisted until the loop below finishes).
            result = BenchmarkResult(
                model=model,
                success=False,
                halted_reason=f"provider_error: {type(e).__name__}: {e}",
                n_retries_total=0,
                latency_seconds=0.0,
                prompt_tokens=0,
                completion_tokens=0,
                estimated_cost_usd=0.0,
                mentions_expected_category=False,
                run_id=run_id,
                timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
        results.append(result)
        print(f"  -> success={result.success} latency={result.latency_seconds}s retries={result.n_retries_total}")

    out_dir = Path("benchmarks/results")
    latest_path = write_latest(results, out_dir)
    history_path = append_history(results, out_dir)

    print("\n--- Benchmark summary ---")
    print(f"{'model':<15}{'success':<10}{'retries':<10}{'latency(s)':<12}{'category_ok':<12}")
    for r in results:
        print(f"{r.model:<15}{str(r.success):<10}{r.n_retries_total:<10}{r.latency_seconds:<12}{str(r.mentions_expected_category):<12}")
    print(f"\nFull results written to {latest_path}")
    print(f"Appended to history: {history_path}")


if __name__ == "__main__":
    main()
