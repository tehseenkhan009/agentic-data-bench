"""
Skill: plausibility_check

Sanity-checks a numeric/tabular analysis result before it is allowed to
reach the Reporter. This is the "does this number make sense" gate that
catches silent LLM/pandas mistakes (off-by-orders-of-magnitude, NaN/inf
results, impossible percentages) that a purely syntactic check would miss.

Results are not auto-rejected for being *surprising* — a big number can be
correct — but surprising results are flagged so the Reviewer can require an
explanation before approving, rather than silently passing them through.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.guardrails import REVIEW_POLICY


@dataclass
class PlausibilityReport:
    passed: bool
    findings: list[str] = field(default_factory=list)
    needs_extra_scrutiny: bool = False


def _is_bad_scalar(x: Any) -> bool:
    try:
        return math.isnan(float(x)) or math.isinf(float(x))
    except (TypeError, ValueError):
        return False


def check(value: Any, *, is_percentage: bool = False, is_growth_rate: bool = False) -> PlausibilityReport:
    findings: list[str] = []
    needs_scrutiny = False

    values_to_check = []
    if isinstance(value, (pd.Series, np.ndarray, list, tuple)):
        values_to_check = list(value)
    elif isinstance(value, pd.DataFrame):
        values_to_check = value.to_numpy().flatten().tolist()
    else:
        values_to_check = [value]

    for v in values_to_check:
        if isinstance(v, (int, float, np.floating, np.integer)) and _is_bad_scalar(v):
            findings.append(f"implausible: NaN/Inf found in result ({v!r})")

    if is_percentage:
        lo, hi = REVIEW_POLICY.percentage_bounds
        for v in values_to_check:
            if isinstance(v, (int, float, np.floating, np.integer)) and not (lo <= float(v) <= hi):
                findings.append(f"implausible: percentage value {v} outside [{lo}, {hi}]")

    if is_growth_rate:
        for v in values_to_check:
            if isinstance(v, (int, float, np.floating, np.integer)) and abs(float(v)) > REVIEW_POLICY.surprising_growth_rate_threshold:
                needs_scrutiny = True

    return PlausibilityReport(passed=len(findings) == 0, findings=findings, needs_extra_scrutiny=needs_scrutiny)
