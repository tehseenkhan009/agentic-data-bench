"""Shared helper for reading token usage off an LLM response, so agents and
the benchmark harness can report real prompt/completion token counts instead
of a hardcoded placeholder.
"""
from __future__ import annotations

from langchain_core.messages import BaseMessage


def usage_from_response(response: BaseMessage) -> dict:
    usage = getattr(response, "usage_metadata", None) or {}
    return {
        "prompt_tokens": usage.get("input_tokens", 0),
        "completion_tokens": usage.get("output_tokens", 0),
    }


def add_usage(*usages: dict) -> dict:
    return {
        "prompt_tokens": sum(u.get("prompt_tokens", 0) for u in usages),
        "completion_tokens": sum(u.get("completion_tokens", 0) for u in usages),
    }
