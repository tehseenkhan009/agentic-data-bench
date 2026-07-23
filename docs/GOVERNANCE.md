# Governance: Agents, Roles, Guardrails, Skills

This document is the single source of truth for how agents in this system are defined, constrained, and reused. In a real enterprise setting this is the artifact a governance process would maintain and review.

## 1. Agent Registry

| Agent | Role | Inputs | Outputs | Allowed skills | Escalation |
|---|---|---|---|---|---|
| **Planner** | Decomposes the user's analysis question into a short, ordered list of concrete analytical steps (e.g. "compute revenue by category", "test trend significance"). | `question`, dataset schema | `plan: list[str]` | none (reasoning-only) | If the question is out of scope (not answerable from the dataset), it must say so and stop the run. |
| **Analyst** | Writes and executes pandas code to carry out one plan step at a time; produces the numeric/tabular result plus a natural-language interpretation. | `plan`, `dataframe`, prior results | `code`, `result`, `interpretation` | `code_execution` | Must not modify the source dataframe in place; must not attempt file/network access. |
| **Reviewer (QA)** | Independently checks the Analyst's output for (a) guardrail violations, (b) static code-quality/security issues, (c) plausibility of the numeric result. | `code`, `result`, `interpretation` | `verdict: pass/fail`, `findings: list[str]` | `static_analysis`, `plausibility_check` | On `fail`, sends the run back to the Analyst with findings attached (max 2 retries), then escalates to the human user if still failing. |
| **Reporter** | Synthesizes the approved plan + results into a final markdown report for the human. | approved results | `report.md` | none (formatting-only) | — |

Each agent has **one job and one owning prompt**. Agents are not allowed to call skills outside their assigned list — this is enforced in code (`src/graph.py`), not just by prompt instruction, because prompt-only restrictions are not a real guardrail.

## 2. Guardrail Policy

Guardrails live in `src/guardrails.py` and are enforced **outside the LLM**, i.e. by deterministic code that runs regardless of what the model outputs. Prompted "please don't do X" is treated as guidance, not a guardrail.

Current guardrails:

1. **Execution sandboxing** — Analyst-generated code runs through `skills/code_execution.py`, which:
   - only allows a fixed set of imports (`pandas`, `numpy`, `math`, `statistics`);
   - blocks `import os`, `import sys`, `subprocess`, `open(`, `eval(`, `exec(`, `__import__`;
   - allows a small whitelist of pure, side-effect-free builtins (`len`, `float`, `int`, `str`, `bool`, `isinstance`, etc.) needed for ordinary correct code, while still excluding anything with I/O or process access;
   - runs with a wall-clock timeout.
   - this guardrail is provider-agnostic: it applies to generated code regardless of which LLM (`src/llm_providers.py` routes OpenAI, Google Gemini, or NVIDIA NIM models) produced it — a capable model reaching for a library outside the whitelist (e.g. `scipy.stats` for significance testing) is rejected the same as any other model.
2. **Static analysis gate** — every piece of generated code is scanned (`skills/static_analysis.py`) for banned patterns and cyclomatic-complexity outliers before it is allowed to run again in a later step.
3. **Plausibility gate** — every numeric result is checked (`skills/plausibility_check.py`) against basic sanity bounds (e.g. percentages within [0,100], no `NaN`/`inf` results, growth rates within a configurable "surprising result" threshold that triggers extra scrutiny rather than auto-acceptance).
4. **Retry ceiling** — the Analyst↔Reviewer loop is capped (default: 2 retries) to avoid infinite loops burning tokens; on ceiling breach the run halts and reports the failure to the user rather than silently returning a low-confidence answer.
5. **No silent scope creep** — the Planner may not introduce steps not derivable from the original question; if it does, the Reviewer flags it.

## 3. Reusable Skills

Skills are the reusable, independently-testable units agents call — the same skill can be reused by future agents, which is the point of registering them centrally rather than inlining logic per-agent.

| Skill | File | Purpose | Used by |
|---|---|---|---|
| `code_execution` | `src/skills/code_execution.py` | Sandboxed execution of generated pandas code | Analyst |
| `static_analysis` | `src/skills/static_analysis.py` | Lints generated code for banned patterns / complexity | Reviewer |
| `plausibility_check` | `src/skills/plausibility_check.py` | Sanity-checks numeric results | Reviewer |

Skills are pure functions with typed inputs/outputs and unit tests (`tests/`) — this is what makes them "reusable" in the governance sense: they can be picked up by a new agent without re-deriving their behavior from a prompt.

## 4. Traceability

`src/graph.py` uses a single typed `AgentState` (TypedDict) threaded through every node. Every node appends a structured entry to `state["trace"]` (agent name, action, input hash, output, guardrail verdict, timestamp). This gives a full, replayable audit trail of a run — required for any process that has to explain *why* an agentic system produced a given answer.

The `dashboard/` app (see README "Observability Dashboard") is the visual layer on top of this same data — it reads `outputs/trace.json` and `benchmarks/results/history.jsonl` directly, with no separate store, so the trace and benchmark history remain the single source of truth described above.

## 5. Change process (how this would work on a real team)

1. Propose a new agent/skill/guardrail change as a PR against this file + its implementation.
2. Reviewer(s) check: does it have a single clear responsibility, an explicit allowed-skill list, and tests?
3. Merge → the benchmark suite (`benchmarks/run_benchmark.py`) is re-run to confirm no quality/cost regression before the change ships.
