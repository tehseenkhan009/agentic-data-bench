"""
Centralized guardrail policy.

Guardrails are deterministic, code-enforced rules — not prompt suggestions.
Every skill that touches generated code or generated results imports its
limits from here, so the policy is defined once and enforced everywhere.

See docs/GOVERNANCE.md section 2 for the rationale behind each rule.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionPolicy:
    allowed_imports: frozenset = field(
        default_factory=lambda: frozenset({"pandas", "numpy", "math", "statistics"})
    )
    banned_tokens: frozenset = field(
        default_factory=lambda: frozenset(
            {
                "import os",
                "import sys",
                "import subprocess",
                "import shutil",
                "__import__",
                "eval(",
                "exec(",
                "open(",
                "input(",
                "socket",
                "requests",
                "urllib",
            }
        )
    )
    timeout_seconds: int = 5


@dataclass(frozen=True)
class ReviewPolicy:
    max_retries: int = 2
    max_cyclomatic_complexity: int = 8
    surprising_growth_rate_threshold: float = 3.0  # 300% — flag for extra scrutiny
    percentage_bounds: tuple = (0.0, 100.0)


EXECUTION_POLICY = ExecutionPolicy()
REVIEW_POLICY = ReviewPolicy()
