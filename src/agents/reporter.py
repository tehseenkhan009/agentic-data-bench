"""
Agent: Reporter

Role: formatting-only. Takes the approved, reviewed results for every plan
step and writes a final markdown report for the human. No skill access,
no new analysis.
"""
from __future__ import annotations

from datetime import datetime, timezone


def build_report(question: str, step_results: list[dict]) -> str:
    lines = [
        f"# Analysis Report",
        "",
        f"**Question:** {question}",
        "",
        f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z_",
        "",
        "## Findings",
        "",
    ]
    for i, step in enumerate(step_results, start=1):
        lines.append(f"### Step {i}: {step['step']}")
        lines.append("")
        lines.append(f"```python\n{step['code']}\n```")
        lines.append("")
        lines.append(f"**Result:** `{step['result']!r}`")
        lines.append("")
        lines.append(f"**Interpretation:** {step['interpretation']}")
        if step.get("needs_extra_scrutiny"):
            lines.append("")
            lines.append("> ⚠️ This result was flagged for extra scrutiny (unusually large magnitude) — review before relying on it.")
        lines.append("")
    return "\n".join(lines)
