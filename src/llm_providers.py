"""Model provider picker.

Routes a model name to the right LangChain chat client by a simple naming
convention, so a model can be swapped across providers (main.py --model flag,
benchmarks/run_benchmark.py MODEL_CONFIGS) by just changing a string — no
other code needs to know which provider is behind it:

  - "gemini-*"      -> Google AI Studio, via GOOGLE_API_KEY  (langchain-google-genai)
  - "org/model"     -> NVIDIA NIM (has a "/", e.g. "meta/llama-3.3-70b-instruct"),
                       an OpenAI-compatible endpoint, via NVIDIA_API_KEY
  - anything else   -> OpenAI, via OPENAI_API_KEY  (langchain-openai)
"""
from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def get_llm(model: str, temperature: float = 0) -> BaseChatModel:
    if model.startswith("gemini-"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, temperature=temperature)

    if "/" in model:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url=NVIDIA_BASE_URL,
            api_key=os.environ["NVIDIA_API_KEY"],
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model, temperature=temperature)


def get_text(response: BaseMessage) -> str:
    """Plain text of a chat response, regardless of provider.

    OpenAI-style models return `.content` as a str; some providers (e.g.
    Gemini via langchain-google-genai) return a list of content blocks
    (`{"type": "text", "text": "..."}` or bare strings) instead.
    """
    content = response.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content)
