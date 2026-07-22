"""
Agent: Analyst

Role: writes pandas code for one plan step at a time, executes it through
the sandboxed `code_execution` skill, and produces a short natural-language
interpretation of the result. Retries with Reviewer feedback appended to
the prompt when a previous attempt failed a guardrail/QA check.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
import pandas as pd

from src.skills import code_execution
from src.llm_usage import usage_from_response, add_usage

SYSTEM_PROMPT = """You are the Analyst agent in a governed multi-agent data-analysis system.

Given one analysis step and a dataframe `df`, write minimal pandas code that computes the \
answer and assigns it to a variable named `result`.

Hard rules (violating these will cause your code to be rejected before it even runs):
- Only use pandas (`pd`), numpy (`np`), math, statistics. No other imports.
- Never use os, sys, subprocess, eval, exec, open, input, network calls.
- Never mutate `df` in place; treat it as read-only.
- Output ONLY the Python code, no markdown fences, no explanation.
"""


@dataclass
class AnalystOutput:
    code: str
    execution: code_execution.ExecutionResult
    interpretation: str
    usage: dict


def _generate_code(llm: BaseChatModel, step: str, columns: list[str], feedback: str | None) -> tuple[str, dict]:
    prompt = f"Dataframe columns: {columns}\n\nStep: {step}\n"
    if feedback:
        prompt += f"\nYour previous attempt was rejected for: {feedback}\nFix it and try again.\n"
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)])
    code = response.content.strip()
    # strip accidental markdown fences
    if code.startswith("```"):
        code = code.strip("`")
        code = code.split("\n", 1)[1] if "\n" in code else code
        if code.lower().startswith("python"):
            code = code.split("\n", 1)[1]
    return code.strip(), usage_from_response(response)


def _interpret(llm: BaseChatModel, step: str, value) -> tuple[str, dict]:
    prompt = f"Step: {step}\nComputed result: {value!r}\n\nGive a one-sentence, plain-language interpretation."
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip(), usage_from_response(response)


def analyze_step(
    llm: BaseChatModel,
    step: str,
    df: pd.DataFrame,
    feedback: str | None = None,
) -> AnalystOutput:
    code, code_usage = _generate_code(llm, step, list(df.columns), feedback)
    execution = code_execution.run(code, df)
    if execution.success:
        interpretation, interpret_usage = _interpret(llm, step, execution.value)
    else:
        interpretation, interpret_usage = "", {}
    usage = add_usage(code_usage, interpret_usage)
    return AnalystOutput(code=code, execution=execution, interpretation=interpretation, usage=usage)
