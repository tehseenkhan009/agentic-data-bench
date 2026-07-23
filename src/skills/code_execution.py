"""
Skill: code_execution

Executes Analyst-generated pandas code against a dataframe in a restricted
namespace. This is intentionally simple (no real OS-level sandbox / container)
because the point of this reference project is to demonstrate the *pattern*
of guardrail-enforced execution, not to ship a production sandbox.

For a production system, replace `_run_restricted` with an actual isolated
subprocess / microVM / gVisor executor.
"""
from __future__ import annotations

import builtins
import math
import statistics
import threading
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.guardrails import EXECUTION_POLICY


class GuardrailViolation(Exception):
    """Raised when generated code violates the execution policy."""


@dataclass
class ExecutionResult:
    success: bool
    value: Any = None
    stdout_repr: str = ""
    error: str | None = None


def _static_precheck(code: str) -> None:
    lowered = code.lower()
    for banned in EXECUTION_POLICY.banned_tokens:
        if banned.lower() in lowered:
            raise GuardrailViolation(f"Banned pattern detected in generated code: '{banned}'")


class _TimeoutError(Exception):
    pass


def _run_restricted(code: str, df: pd.DataFrame) -> Any:
    """Executes `code` with `df` bound as `df`, in a restricted namespace.

    The last expression's value should be assigned to a variable named
    `result` by the generated code; we return that.
    """
    safe_builtins = {
        name: getattr(builtins, name)
        for name in (
            "len", "range", "min", "max", "sum", "round", "sorted", "abs", "enumerate", "zip",
            "list", "dict", "tuple", "set",
            # Pure, side-effect-free type constructors/checks — no I/O, no process/
            # filesystem access, so they carry none of the risk `eval`/`exec`/`open`
            # (already banned above) do. Their absence was rejecting ordinary,
            # correct analysis code (e.g. `float(slope)`) as if it were a violation.
            "float", "int", "str", "bool", "isinstance", "type",
        )
    }
    restricted_globals = {
        "__builtins__": safe_builtins,
        "pd": pd,
        "np": np,
        "math": math,
        "statistics": statistics,
        "df": df.copy(deep=True),  # never let generated code mutate the source df
    }
    local_ns: dict[str, Any] = {}
    exec_error: list[BaseException] = []

    def _target() -> None:
        try:
            exec(code, restricted_globals, local_ns)  # noqa: S102 - guarded by policy above
        except BaseException as e:  # noqa: BLE001 - re-raised on the calling thread below
            exec_error.append(e)

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    worker.join(EXECUTION_POLICY.timeout_seconds)
    if worker.is_alive():
        # Can't forcibly kill a thread; the demo sandbox just abandons it and
        # reports a timeout (see module docstring re: production sandboxing).
        raise _TimeoutError("Execution exceeded guardrail timeout")
    if exec_error:
        raise exec_error[0]

    if "result" not in local_ns:
        raise GuardrailViolation("Generated code must assign its output to a variable named `result`.")
    return local_ns["result"]


def run(code: str, df: pd.DataFrame) -> ExecutionResult:
    """Public entry point: validate then execute generated code.

    Returns an ExecutionResult instead of raising, so the calling agent
    graph can route failures back to the Analyst/Reviewer loop cleanly.
    """
    try:
        _static_precheck(code)
        value = _run_restricted(code, df)
        return ExecutionResult(success=True, value=value, stdout_repr=repr(value))
    except GuardrailViolation as e:
        return ExecutionResult(success=False, error=f"guardrail_violation: {e}")
    except _TimeoutError as e:
        return ExecutionResult(success=False, error=f"timeout: {e}")
    except Exception as e:  # noqa: BLE001 - we want to capture and route, not crash the run
        return ExecutionResult(success=False, error=f"execution_error: {type(e).__name__}: {e}")
