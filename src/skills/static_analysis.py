"""
Skill: static_analysis

Lightweight static QA over generated code, used by the Reviewer agent.
Checks two things:
  1. banned-pattern security scan (same policy source as code_execution,
     re-checked here independently — defense in depth)
  2. a crude cyclomatic-complexity proxy, to catch generated code that has
     spiraled into unnecessarily convoluted branching (a real quality smell
     for LLM-generated snippets)
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

from src.guardrails import EXECUTION_POLICY, REVIEW_POLICY


@dataclass
class StaticAnalysisReport:
    passed: bool
    findings: list[str] = field(default_factory=list)
    complexity: int = 0


def _security_scan(code: str) -> list[str]:
    findings = []
    lowered = code.lower()
    for banned in EXECUTION_POLICY.banned_tokens:
        if banned.lower() in lowered:
            findings.append(f"security: banned pattern '{banned}' present")
    return findings


def _cyclomatic_complexity(code: str) -> int:
    """A simplified McCabe-style count: 1 + number of branching nodes."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 999  # unparsable code is treated as maximally complex/unsafe

    branch_nodes = (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp, ast.comprehension)
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, branch_nodes):
            complexity += 1
    return complexity


def analyze(code: str) -> StaticAnalysisReport:
    findings = _security_scan(code)
    complexity = _cyclomatic_complexity(code)

    if complexity > REVIEW_POLICY.max_cyclomatic_complexity:
        findings.append(
            f"quality: cyclomatic complexity {complexity} exceeds policy limit "
            f"{REVIEW_POLICY.max_cyclomatic_complexity}"
        )

    return StaticAnalysisReport(passed=len(findings) == 0, findings=findings, complexity=complexity)
