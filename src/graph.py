"""
Workflow: LangGraph StateGraph wiring Planner -> Analyst -> Reviewer -> Reporter,
with a bounded Analyst<->Reviewer retry loop (guardrails.REVIEW_POLICY.max_retries).

A single typed AgentState is threaded through every node and every node
appends a structured entry to state["trace"], giving a full, replayable
audit trail of the run (see docs/GOVERNANCE.md section 4).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict, Annotated
import operator

import pandas as pd
from langgraph.graph import StateGraph, END
from langchain_core.language_models.chat_models import BaseChatModel

from src.agents import planner, analyst, reviewer, reporter
from src.guardrails import REVIEW_POLICY


class AgentState(TypedDict):
    question: str
    df: pd.DataFrame
    plan: list[str]
    current_step_idx: int
    retries_this_step: int
    feedback: str | None
    step_results: list[dict]
    report: str
    halted_reason: str | None
    trace: Annotated[list[dict], operator.add]
    # transient hand-off fields between the Analyst and Reviewer nodes
    pending_code: str
    pending_success: bool
    pending_value: object
    pending_error: str | None
    pending_interpretation: str


def _log(agent: str, action: str, details: dict) -> list[dict]:
    return [
        {
            "agent": agent,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **details,
        }
    ]


def build_graph(llm: BaseChatModel):
    def planner_node(state: AgentState) -> dict:
        steps = planner.plan(llm, state["question"], list(state["df"].columns))
        if not steps:
            return {
                "plan": [],
                "halted_reason": "Planner determined the question cannot be answered from this dataset.",
                "trace": _log("Planner", "plan", {"steps": steps, "halted": True}),
            }
        return {
            "plan": steps,
            "current_step_idx": 0,
            "trace": _log("Planner", "plan", {"steps": steps}),
        }

    def analyst_node(state: AgentState) -> dict:
        step = state["plan"][state["current_step_idx"]]
        output = analyst.analyze_step(llm, step, state["df"], feedback=state.get("feedback"))
        return {
            "pending_code": output.code,
            "pending_success": output.execution.success,
            "pending_value": output.execution.value,
            "pending_error": output.execution.error,
            "pending_interpretation": output.interpretation,
            "trace": _log(
                "Analyst",
                "generate_and_execute",
                {"step": step, "code": output.code, "success": output.execution.success,
                 "error": output.execution.error},
            ),
        }

    def reviewer_node(state: AgentState) -> dict:
        # Reconstruct a lightweight AnalystOutput-shaped object from the typed
        # state fields the Analyst node wrote, so reviewer.review() stays
        # decoupled from the graph's state shape.
        output = analyst.AnalystOutput(
            code=state["pending_code"],
            execution=analyst.code_execution.ExecutionResult(
                success=state["pending_success"],
                value=state["pending_value"],
                error=state["pending_error"],
            ),
            interpretation=state["pending_interpretation"],
        )
        verdict = reviewer.review(output)

        if verdict.passed:
            step_record = {
                "step": state["plan"][state["current_step_idx"]],
                "code": output.code,
                "result": output.execution.value,
                "interpretation": output.interpretation,
                "needs_extra_scrutiny": verdict.needs_extra_scrutiny,
            }
            return {
                "step_results": state["step_results"] + [step_record],
                "current_step_idx": state["current_step_idx"] + 1,
                "retries_this_step": 0,
                "feedback": None,
                "trace": _log("Reviewer", "review", {"passed": True, "findings": verdict.findings}),
            }

        retries = state["retries_this_step"] + 1
        if retries > REVIEW_POLICY.max_retries:
            return {
                "halted_reason": (
                    f"Step '{state['plan'][state['current_step_idx']]}' failed QA "
                    f"after {REVIEW_POLICY.max_retries} retries: {verdict.findings}"
                ),
                "trace": _log("Reviewer", "review", {"passed": False, "findings": verdict.findings, "retry_ceiling_hit": True}),
            }
        return {
            "retries_this_step": retries,
            "feedback": "; ".join(verdict.findings),
            "trace": _log("Reviewer", "review", {"passed": False, "findings": verdict.findings, "retry": retries}),
        }

    def reporter_node(state: AgentState) -> dict:
        report_md = reporter.build_report(state["question"], state["step_results"])
        return {"report": report_md, "trace": _log("Reporter", "build_report", {"length": len(report_md)})}

    def route_after_planner(state: AgentState) -> str:
        return "halt" if state.get("halted_reason") else "analyst"

    def route_after_reviewer(state: AgentState) -> str:
        if state.get("halted_reason"):
            return "halt"
        if state["current_step_idx"] >= len(state["plan"]):
            return "reporter"
        return "analyst"

    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("reporter", reporter_node)

    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", route_after_planner, {"analyst": "analyst", "halt": END})
    graph.add_edge("analyst", "reviewer")
    graph.add_conditional_edges(
        "reviewer", route_after_reviewer, {"analyst": "analyst", "reporter": "reporter", "halt": END}
    )
    graph.add_edge("reporter", END)

    return graph.compile()


def initial_state(question: str, df: pd.DataFrame) -> AgentState:
    return AgentState(
        question=question,
        df=df,
        plan=[],
        current_step_idx=0,
        retries_this_step=0,
        feedback=None,
        step_results=[],
        report="",
        halted_reason=None,
        trace=[],
        pending_code="",
        pending_success=False,
        pending_value=None,
        pending_error=None,
        pending_interpretation="",
    )
