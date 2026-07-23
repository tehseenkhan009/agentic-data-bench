"""Unit tests for the model-provider picker (src/llm_providers.py).

get_llm() only constructs a client object — no network calls happen until
.invoke() — so routing can be tested without hitting any real API, as long
as a dummy API key is present for construction-time validation.
"""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from src.llm_providers import NVIDIA_BASE_URL, get_llm, get_text


@pytest.fixture(autouse=True)
def dummy_api_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("NVIDIA_API_KEY", "test-nvidia-key")


class TestGetLlmRouting:
    def test_plain_model_name_routes_to_openai(self):
        from langchain_openai import ChatOpenAI

        llm = get_llm("gpt-4o-mini")
        assert isinstance(llm, ChatOpenAI)

    def test_gemini_prefixed_model_routes_to_google(self):
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = get_llm("gemini-2.0-flash")
        assert isinstance(llm, ChatGoogleGenerativeAI)

    def test_slash_model_routes_to_nvidia_via_openai_compatible_client(self):
        from langchain_openai import ChatOpenAI

        llm = get_llm("meta/llama-3.3-70b-instruct")
        assert isinstance(llm, ChatOpenAI)
        assert str(llm.openai_api_base) == NVIDIA_BASE_URL


class TestGetText:
    def test_plain_string_content(self):
        assert get_text(AIMessage(content="hello")) == "hello"

    def test_list_of_text_blocks_content(self):
        message = AIMessage(content=[{"type": "text", "text": "hello "}, {"type": "text", "text": "world"}])
        assert get_text(message) == "hello world"

    def test_list_with_bare_strings(self):
        message = AIMessage(content=["hello ", "world"])
        assert get_text(message) == "hello world"
