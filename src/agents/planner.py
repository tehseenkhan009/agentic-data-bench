"""
Agent: Planner

Role (see docs/GOVERNANCE.md): decomposes the user's question into a short,
ordered list of concrete, dataframe-answerable analytical steps. Reasoning
only — no skill access, no code execution.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel

from src.llm_usage import usage_from_response

SYSTEM_PROMPT = """You are the Planner agent in a governed multi-agent data-analysis system.

Your ONLY job: turn the user's analysis question into 2-4 short, concrete, \
ordered steps that can each be answered with pandas code against the given dataframe.

Rules:
- Only propose steps that are answerable from the columns provided. If the question \
cannot be answered from this data, say so explicitly and return an empty plan.
- Do not write code. Do not answer the question yourself.
- Keep each step to one sentence.

Output format (strict): a numbered list, nothing else.
"""


@dataclass
class PlanResult:
    steps: list[str]
    usage: dict


def plan(llm: BaseChatModel, question: str, columns: list[str]) -> PlanResult:
    prompt = (
        f"Dataframe columns: {columns}\n\n"
        f"User question: {question}\n\n"
        "Return the numbered plan now."
    )
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)])
    lines = [line.strip() for line in response.content.splitlines() if line.strip()]
    steps = []
    for line in lines:
        # strip "1. ", "1)", "- " style prefixes
        cleaned = line.lstrip("0123456789.)- ").strip()
        if cleaned:
            steps.append(cleaned)
    return PlanResult(steps=steps, usage=usage_from_response(response))
