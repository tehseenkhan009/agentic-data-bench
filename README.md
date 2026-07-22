# AgentBench — Governed Multi-Agent Data Analysis & Benchmarking Pipeline

A small but complete **multi-agent system**, built with **LangGraph**, that plans, executes, quality-checks and reports on data-analysis tasks — while systematically **benchmarking which model/agent configuration gets the best result for the lowest cost**.

The project was built as a practical showcase for agentic AI / multi-agent engineering work: governance of agent roles, reusable skills, guardrails, QA integration, and empirical benchmarking of models and workflow variants.

## Why this project

It intentionally mirrors the core responsibilities of an "Agentic AI / Multi-Agent Systems" role:

| Responsibility | Where it lives in this repo |
|---|---|
| Co-develop AI agents for engineering/enterprise tasks | `src/agents/` — Planner, Analyst, Reviewer, Reporter |
| Governance: agent definitions, role descriptions, guardrails, reusable skills | `docs/GOVERNANCE.md`, `src/guardrails.py`, `src/skills/` |
| Structure & optimize agent workflows for quality, traceability, efficiency | `src/graph.py` (LangGraph `StateGraph`, typed state, full run trace) |
| Integrate QA mechanisms (security, code quality, plausibility) | `src/skills/static_analysis.py`, `src/skills/plausibility.py` |
| Benchmark & validate models/agents/workflow variants against defined criteria | `benchmarks/run_benchmark.py` |
| Translate findings into a working PoC | this whole repo |
| Document methods, interfaces, results | `docs/`, docstrings, `benchmarks/results/` |

## Architecture

```
                     ┌─────────────┐
   user question  →  │   Planner   │  breaks the analysis goal into steps
                     └──────┬──────┘
                            ▼
                     ┌─────────────┐
                     │   Analyst   │  writes & executes pandas code (sandboxed)
                     └──────┬──────┘
                            ▼
                     ┌─────────────┐
                     │  Reviewer   │  guardrails + static analysis + plausibility check
                     └──────┬──────┘
                       fail │ pass
                    ┌───────┴────────┐
                    ▼                ▼
             back to Analyst   ┌─────────────┐
             (max 2 retries)   │  Reporter   │  writes the final markdown report
                               └─────────────┘
```

Every node reads/writes a single typed `AgentState` object, so the whole run is traceable end-to-end (see `src/graph.py`).

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY (or swap the model client)

python main.py --data data/sample_sales.csv --question "Which product category has the strongest revenue growth trend, and is it statistically robust or driven by outliers?"
```

Output: a run trace in the console plus `outputs/report.md`.

## Benchmarking models & configurations

```bash
python benchmarks/run_benchmark.py
```

This runs the same task across multiple model configurations (e.g. `gpt-4o-mini` vs `gpt-4o`, with/without the Reviewer loop) and scores each run on **correctness, guardrail pass rate, latency, and estimated token cost**, writing a comparison table to `benchmarks/results/`. The goal, per the job spec, is finding the smallest/cheapest model that still clears the quality bar — not just the most capable one.

## Project layout

```
agentic-data-bench/
├── docs/
│   └── GOVERNANCE.md        # agent roles, guardrails spec, skill registry
├── src/
│   ├── agents/               # one file per agent role
│   ├── skills/                # reusable, testable capabilities agents call
│   ├── guardrails.py          # centralized guardrail policy + enforcement
│   └── graph.py                # LangGraph workflow definition
├── benchmarks/
│   └── run_benchmark.py       # multi-model / multi-config evaluation harness
├── tests/                      # unit tests for guardrails & skills
├── data/sample_sales.csv       # toy dataset for the demo
└── main.py                     # CLI entry point
```

## Notes on scope

This is a deliberately compact reference implementation — built to demonstrate the *patterns* (governance, guardrails, reusable skills, QA-in-the-loop, benchmarking) clearly and correctly, not to be a production system. Extending it (more agents, a real sandbox executor, a vector-store skill, async parallel benchmarking) would be natural next steps.
