"""
Agent: Reviewer (QA)

Role: independently checks the Analyst's output against the guardrail
policy using the static_analysis and plausibility_check skills, and
decides pass/fail. This agent does not call an LLM for the checks
themselves (deterministic QA), though it can optionally use one to
phrase the feedback sent back to the Analyst.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.agents.analyst import AnalystOutput
from src.skills import static_analysis, plausibility_check


@dataclass
class ReviewVerdict:
    passed: bool
    findings: list[str] = field(default_factory=list)
    needs_extra_scrutiny: bool = False


def review(analyst_output: AnalystOutput) -> ReviewVerdict:
    findings: list[str] = []

    if not analyst_output.execution.success:
        return ReviewVerdict(passed=False, findings=[analyst_output.execution.error or "execution failed"])

    static_report = static_analysis.analyze(analyst_output.code)
    findings.extend(static_report.findings)

    plaus_report = plausibility_check.check(analyst_output.execution.value)
    findings.extend(plaus_report.findings)

    passed = static_report.passed and plaus_report.passed
    return ReviewVerdict(passed=passed, findings=findings, needs_extra_scrutiny=plaus_report.needs_extra_scrutiny)
