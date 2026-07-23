"""FastAPI app for the AgentBench observability dashboard.

Intentionally thin: it only reads the two local files that are already the
source of truth elsewhere in the repo and hands back their parsed contents
(plus a small aggregation for the benchmark history). All real logic lives
in data.py so it stays unit-testable without spinning up HTTP.

Run from the repo root:
    uvicorn dashboard.backend.main:app --reload
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dashboard.backend.data import aggregate_by_model, load_benchmark_history, load_trace

REPO_ROOT = Path(__file__).resolve().parents[2]
TRACE_PATH = REPO_ROOT / "outputs" / "trace.json"
HISTORY_PATH = REPO_ROOT / "benchmarks" / "results" / "history.jsonl"

app = FastAPI(title="AgentBench Observability Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/trace")
def get_trace() -> dict:
    return {"trace": load_trace(TRACE_PATH)}


@app.get("/api/benchmark-history")
def get_benchmark_history() -> dict:
    history = load_benchmark_history(HISTORY_PATH)
    return {"history": history, "summary": aggregate_by_model(history)}
