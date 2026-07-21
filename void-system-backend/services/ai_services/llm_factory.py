"""Model factories built from the canonical connection profile."""
from __future__ import annotations

from contextlib import contextmanager
from urllib.parse import urlparse
from contextvars import ContextVar
from typing import Any, Iterator, Optional

from core.model_connection_profile import (
    ModelConnectionError,
    resolve_chat_connection,
    resolve_embedding_connection,
)
from core.runtime_settings import RuntimeSettings


_active_runtime_settings: ContextVar[Optional[RuntimeSettings]] = ContextVar(
    "void_system_active_runtime_settings", default=None
)


@contextmanager
def runtime_settings_scope(settings: RuntimeSettings) -> Iterator[None]:
    """Bind application-owned settings while a legacy adapter invokes AI code.

    Callers: HTTP dependency composition and legacy adapters that do not yet
    accept settings directly. The binding is request-local and always restored,
    so concurrent requests cannot leak an administrator's active profile into
    one another.
    """
    token = _active_runtime_settings.set(settings)
    try:
        yield
    finally:
        _active_runtime_settings.reset(token)


def active_runtime_settings() -> Optional[RuntimeSettings]:
    """Return request-scoped settings for adapters pending direct injection."""
    return _active_runtime_settings.get()


def _resolve_runtime(settings: Optional[RuntimeSettings]) -> RuntimeSettings:
    """Resolve explicit, request-scoped, or process-startup runtime settings.

    HTTP requests always receive the application-owned snapshot through direct
    injection or ``runtime_settings_scope``. The final branch only supports
    standalone scripts and never reintroduces the retired global Config class.
    """
    return settings or active_runtime_settings() or RuntimeSettings.from_environment()


def _requires_compatible_streaming(provider: str, base_url: Optional[str]) -> bool:
    """Return whether a custom OpenAI gateway must stream visible text.

    Inputs:
        provider: Canonical provider from the active connection profile.
        base_url: Normalized endpoint for that profile.
    Output:
        True only for an openai configuration targeting a non-official host.
    Called by:
        get_chat_llm while composing a ChatOpenAI client.
    Side effects:
        None; LangChain aggregates streamed chunks before invoke() returns.
    Failure:
        Missing or malformed URLs default to False; resolver validation owns the
        actual endpoint error.
    Invariant:
        The runtime transport matches the administrator probe visible-text
        fallback for custom gateways, while api.openai.com keeps its native mode.
    """
    if provider != "openai":
        return False
    try:
        hostname = (urlparse(base_url or "").hostname or "").lower()
    except ValueError:
        return False
    return bool(hostname and hostname != "api.openai.com")


def _supports_openai_responses_api(provider: str, base_url: Optional[str]) -> bool:
    """Allow LangChain's Responses API only for the official OpenAI endpoint.

    Inputs:
        provider: Canonical provider selected in ModelConnectionProfile.
        base_url: Normalized OpenAI protocol root for the active runtime snapshot.
    Output:
        True only when LangChain may safely infer Responses API behavior.
    Called by:
        get_chat_llm before constructing ChatOpenAI.
    Side effects:
        None.
    Failure:
        Malformed or absent URLs deliberately resolve to False so a compatible
        endpoint stays on the explicitly verified /chat/completions protocol.
    Invariant:
        A custom gateway never changes wire protocol merely because a model name
        resembles an official GPT-5 family name.
    """
    if provider != "openai":
        return False
    try:
        hostname = (urlparse(base_url or "").hostname or "").lower()
    except ValueError:
        return False
    return hostname == "api.openai.com"


def _supports_openai_json_mode(provider: str, base_url: Optional[str]) -> bool:
    """Return whether an OpenAI-protocol endpoint can receive response_format.

    Official OpenAI and dedicated local providers implement native JSON mode.
    Generic OpenAI-compatible gateways vary widely: some accept the field but
    fail while streaming a real structured response. Those gateways rely on the
    caller prompt plus local schema validation instead of an unreliable wire
    capability.
    """
    return provider != "openai" or _supports_openai_responses_api(provider, base_url)


def get_chat_llm(
    temperature: float = 0.5,
    json_mode: bool = False,
    streaming: Optional[bool] = None,
    settings: Optional[RuntimeSettings] = None,
) -> Any:
    """Create a chat client from the same profile used by administration probes.

    Inputs: generation temperature, optional JSON mode, an optional streaming
    override, and an explicit runtime settings snapshot. Output: a LangChain
    chat model. Errors: raises ModelConnectionError for invalid configuration
    and preserves upstream client construction errors. No provider or model
    fallback is performed.

    The default preserves the transport selected for interactive chat. Structured
    callers normally keep that provider-specific choice: LangChain aggregates
    compatible SSE chunks into one complete response for invoke().
    """
    profile = resolve_chat_connection(_resolve_runtime(settings))
    if profile.protocol == "ollama":
        from langchain_ollama import ChatOllama

        kwargs: dict[str, Any] = {
            "model": profile.model,
            "base_url": profile.base_url,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["format"] = "json"
        if streaming is False:
            kwargs["disable_streaming"] = True
        return ChatOllama(**kwargs)

    if profile.protocol == "openai":
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": profile.model,
            "temperature": temperature,
            "api_key": profile.api_key,
            "base_url": profile.base_url,
        }
        # LangChain infers the Responses API from GPT-5-like model names. That
        # inference is valid for api.openai.com but can produce empty messages
        # from OpenAI-compatible gateways that only verify chat completions.
        if not _supports_openai_responses_api(profile.provider, profile.base_url):
            kwargs["use_responses_api"] = False
        if streaming is not None:
            kwargs["streaming"] = streaming
        elif _requires_compatible_streaming(profile.provider, profile.base_url):
            kwargs["streaming"] = True
        if profile.extra_body:
            kwargs["extra_body"] = dict(profile.extra_body)
        if json_mode and _supports_openai_json_mode(profile.provider, profile.base_url):
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
        return ChatOpenAI(**kwargs)

    if profile.protocol == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        kwargs = {
            "model": profile.model,
            "temperature": temperature,
            "google_api_key": profile.api_key,
        }
        if streaming is not None:
            kwargs["streaming"] = streaming
        return ChatGoogleGenerativeAI(**kwargs)

    raise ModelConnectionError(
        f"Unsupported resolved chat protocol: {profile.protocol}.",
        "AI_PROTOCOL_NOT_SUPPORTED",
    )


def chat_output_limit_options(
    *,
    max_tokens: int,
    settings: Optional[RuntimeSettings] = None,
) -> dict[str, int]:
    """Return the provider-native output-limit field for a chat invocation.

    Inputs:
        max_tokens: Provider-neutral requested output budget.
        settings: Optional runtime settings snapshot used for connection resolution.
    Output:
        A one-key mapping that can be passed to ChatModel.bind.
    Callers:
        Structured AI features such as profile inference. They must use this
        helper instead of binding an OpenAI-specific field directly.
    Failure:
        Invalid or incomplete chat configuration raises ModelConnectionError
        through the canonical connection resolver.
    Invariant:
        Ollama receives num_predict; Gemini receives max_output_tokens;
        OpenAI-compatible transports receive max_tokens.
    """
    if max_tokens < 1:
        raise ValueError("max_tokens must be positive.")
    profile = resolve_chat_connection(_resolve_runtime(settings))
    if profile.protocol == "ollama":
        return {"num_predict": max_tokens}
    if profile.protocol == "gemini":
        return {"max_output_tokens": max_tokens}
    return {"max_tokens": max_tokens}


def get_embeddings(settings: Optional[RuntimeSettings] = None) -> Any:
    """Create embeddings from the canonical embedding connection profile.

    Inputs: optional explicit settings. Output: a LangChain embeddings client.
    LM Studio is deliberately not silently treated as an embedding provider;
    callers receive a stable configuration error until a verified provider is
    selected.
    """
    profile = resolve_embedding_connection(_resolve_runtime(settings))
    if profile.protocol == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=profile.model, base_url=profile.base_url)
    if profile.protocol == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=profile.model,
            api_key=profile.api_key,
            base_url=profile.base_url,
        )
    raise ModelConnectionError(
        f"Unsupported resolved embedding protocol: {profile.protocol}.",
        "AI_EMBEDDING_PROTOCOL_NOT_SUPPORTED",
    )
