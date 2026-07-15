"""Factory functions for models selected by an explicit runtime configuration."""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from config import config
from core.runtime_settings import RuntimeSettings


logger = logging.getLogger("void-system-llm-factory")

_active_runtime_settings: ContextVar[Optional[RuntimeSettings]] = ContextVar(
    "void_system_active_runtime_settings", default=None
)


@contextmanager
def runtime_settings_scope(settings: RuntimeSettings):
    """Bind application-owned settings while a legacy adapter invokes AI code."""
    token = _active_runtime_settings.set(settings)
    try:
        yield
    finally:
        _active_runtime_settings.reset(token)


def active_runtime_settings() -> Optional[RuntimeSettings]:
    """Return request-scoped settings for adapters that cannot accept parameters yet."""
    return _active_runtime_settings.get()


def _resolve_runtime(settings: Optional[RuntimeSettings]) -> RuntimeSettings:
    return settings or active_runtime_settings() or config


def get_chat_llm(
    temperature: float = 0.5,
    json_mode: bool = False,
    settings: Optional[RuntimeSettings] = None,
) -> Any:
    """Build a chat model from the supplied application settings.

    The legacy global configuration remains a compatibility fallback for callers
    outside application composition. New paths should always pass settings.
    """
    runtime = _resolve_runtime(settings)
    provider = runtime.LLM_PROVIDER.lower()
    logger.info("Initializing chat provider=%s model=%s", provider, runtime.CHAT_MODEL)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        kwargs = {
            "model": _resolve_ollama_chat_model(runtime.CHAT_MODEL, runtime.OLLAMA_BASE_URL),
            "base_url": runtime.OLLAMA_BASE_URL,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["format"] = "json"
        return ChatOllama(**kwargs)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        _require_key("OPENAI_API_KEY", settings=runtime)
        return ChatOpenAI(model=runtime.CHAT_MODEL, temperature=temperature, api_key=runtime.OPENAI_API_KEY)
    if provider == "deepseek":
        from langchain_openai import ChatOpenAI

        _require_key("OPENAI_API_KEY", "DeepSeek uses OPENAI_API_KEY", runtime)
        return ChatOpenAI(
            model=runtime.CHAT_MODEL or "deepseek-chat",
            temperature=temperature,
            api_key=runtime.OPENAI_API_KEY,
            base_url=runtime.OPENAI_BASE_URL or "https://api.deepseek.com/v1",
        )
    if provider in {"openai_compat", "compatible"}:
        from langchain_openai import ChatOpenAI

        _require_key("OPENAI_API_KEY", "Set OPENAI_API_KEY for the compatible provider", runtime)
        _require_key("OPENAI_BASE_URL", "Set OPENAI_BASE_URL for the compatible provider", runtime)
        return ChatOpenAI(
            model=runtime.CHAT_MODEL,
            temperature=temperature,
            api_key=runtime.OPENAI_API_KEY,
            base_url=runtime.OPENAI_BASE_URL,
        )
    if provider in {"lmstudio", "lm_studio"}:
        from langchain_openai import ChatOpenAI

        # LM Studio exposes the OpenAI chat protocol locally and accepts a
        # placeholder token. Keeping this provider explicit avoids persisting a
        # real cloud secret solely to test a local model.
        return ChatOpenAI(
            model=runtime.CHAT_MODEL,
            temperature=temperature,
            api_key="lm-studio",
            base_url=runtime.OPENAI_BASE_URL or "http://127.0.0.1:1234/v1",
        )
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        _require_key("GOOGLE_API_KEY", settings=runtime)
        return ChatGoogleGenerativeAI(
            model=runtime.CHAT_MODEL or "gemini-1.5-flash",
            temperature=temperature,
            google_api_key=runtime.GOOGLE_API_KEY,
        )

    logger.warning("Unknown LLM provider=%s; falling back to Ollama", provider)
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=_resolve_ollama_chat_model(runtime.CHAT_MODEL, runtime.OLLAMA_BASE_URL),
        base_url=runtime.OLLAMA_BASE_URL,
        temperature=temperature,
    )


def get_embeddings(settings: Optional[RuntimeSettings] = None) -> Any:
    """Build embeddings from the supplied application settings."""
    runtime = _resolve_runtime(settings)
    provider = runtime.EMBEDDING_PROVIDER.lower()
    logger.info("Initializing embeddings provider=%s model=%s", provider, runtime.EMBEDDING_MODEL)

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=runtime.EMBEDDING_MODEL, base_url=runtime.OLLAMA_BASE_URL)
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        _require_key("OPENAI_API_KEY", settings=runtime)
        return OpenAIEmbeddings(
            model=runtime.EMBEDDING_MODEL or "text-embedding-3-small",
            api_key=runtime.OPENAI_API_KEY,
            base_url=runtime.OPENAI_BASE_URL or None,
        )
    if provider == "huggingface":
        raise EnvironmentError(
            "HuggingFace embeddings must be configured by the vector adapter, not llm_factory."
        )

    logger.warning("Unknown embeddings provider=%s; falling back to Ollama", provider)
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(model=runtime.EMBEDDING_MODEL, base_url=runtime.OLLAMA_BASE_URL)


def _require_key(
    key_name: str,
    hint: str = "",
    settings: Optional[RuntimeSettings] = None,
) -> None:
    if getattr(settings or config, key_name, None):
        return
    message = f"Missing required configuration: {key_name}"
    if hint:
        message = f"{message} ({hint})"
    raise EnvironmentError(message)


def _resolve_ollama_chat_model(configured: str, base_url: str) -> str:
    preferred = str(configured or "").strip()
    available = _list_ollama_models(base_url)
    if not preferred:
        return available[0] if available else preferred
    if not available or preferred in available:
        return preferred
    logger.warning("Configured Ollama model=%s is unavailable; using %s", preferred, available[0])
    return available[0]


def _list_ollama_models(base_url: str) -> List[str]:
    base = str(base_url or "http://127.0.0.1:11434").rstrip("/")
    try:
        with urlopen(f"{base}/api/tags", timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, ValueError):
        return []
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return []
    return [str(row["name"]) for row in models if isinstance(row, dict) and row.get("name")]
