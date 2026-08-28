"""Provider-agnostic chat model + a strict-JSON helper.

gemini (langchain-google-genai) or openai (langchain-openai; also covers
OpenAI-compatible gateways such as OpenRouter via OPENAI_BASE_URL).
LangChain imports are lazy so the app boots without the AI stack.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from app.config import settings
from app.logging_config import get_logger

log = get_logger(__name__)


class LLMUnavailable(RuntimeError):
    pass


def configure_langsmith() -> None:
    if not (settings.langsmith_tracing and settings.langsmith_api_key):
        return
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.langsmith_endpoint)
    log.info("LangSmith tracing enabled (project=%s)", settings.langsmith_project)


def ai_enabled() -> bool:
    return settings.ai_enabled


@lru_cache(maxsize=2)
def get_chat_model(temperature: float | None = None) -> Any:
    provider = settings.llm_provider.lower()
    temp = settings.llm_temperature if temperature is None else temperature
    if not settings.active_api_key:
        raise LLMUnavailable(f"No API key for provider '{provider}'.")
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_chat_model,
            google_api_key=settings.google_api_key,
            temperature=temp,
            timeout=settings.llm_timeout_seconds,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_chat_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
            temperature=temp,
            timeout=settings.llm_timeout_seconds,
        )
    raise LLMUnavailable(f"Unknown LLM_PROVIDER '{provider}'.")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.strip()


def llm_json(system: str, user: str) -> dict | list | None:
    """Call the model and parse a strict-JSON reply. Returns None on any failure
    so callers can fall back to deterministic output."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        raw = (
            get_chat_model()
            .invoke([SystemMessage(content=system), HumanMessage(content=user)])
            .content
        )
        return json.loads(_strip_fences(raw))
    except Exception as exc:
        log.warning("llm_json failed, caller will fall back: %s", exc)
        return None


def reset_caches() -> None:
    get_chat_model.cache_clear()
