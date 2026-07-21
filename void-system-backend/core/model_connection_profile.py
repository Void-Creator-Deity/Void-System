"""Canonical, provider-neutral model connection resolution.

This module translates administrator-facing model settings into concrete
protocol, endpoint, credential, and request-option decisions. Administration
probes and runtime clients consume the same ModelConnectionProfile so a
successful connection test represents the configuration used at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


SUPPORTED_CHAT_PROVIDERS = frozenset(
    {"ollama", "openai", "deepseek", "gemini", "openai_compat", "lmstudio"}
)
SUPPORTED_EMBEDDING_PROVIDERS = frozenset({"ollama", "openai"})

_PROVIDER_ALIASES = {"compatible": "openai_compat", "lm_studio": "lmstudio"}
_FORM_FIELD_TO_SETTING = {
    "llm_provider": "LLM_PROVIDER",
    "embedding_provider": "EMBEDDING_PROVIDER",
    "ollama_base_url": "OLLAMA_BASE_URL",
    "chat_model": "CHAT_MODEL",
    "embedding_model": "EMBEDDING_MODEL",
    "openai_base_url": "OPENAI_BASE_URL",
    "openai_api_key": "OPENAI_API_KEY",
    "google_api_key": "GOOGLE_API_KEY",
}


class ModelConnectionError(ValueError):
    """Safe, stable error raised when a model connection cannot be resolved.

    Callers: administration routes, LangChain factories, and AI HTTP routes.
    The code lets all callers map the same root cause to an actionable response
    without exposing credentials.
    """

    def __init__(self, message: str, code: str = "AI_CONFIGURATION_INVALID") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class ModelConnectionProfile:
    """Immutable, fully normalized upstream model connection.

    Inputs come from application-owned runtime settings plus optional unsaved
    administration form values. Outputs are safe to pass to HTTP probes or
    LangChain constructors. extra_body only contains protocol options. LM Studio
    disables visible reasoning tokens for both probes and streaming runtime.
    """

    purpose: str
    provider: str
    protocol: str
    base_url: Optional[str]
    api_key: Optional[str]
    model: str
    is_local: bool = False
    extra_body: Mapping[str, Any] = field(default_factory=dict)

    @property
    def request_body_options(self) -> Mapping[str, Any]:
        """Return provider request fields shared by probes and runtime clients."""
        return self.extra_body

    def public_diagnostics(self) -> dict[str, Any]:
        """Return credential-free values for diagnostics and audit events."""
        return {
            "purpose": self.purpose,
            "provider": self.provider,
            "protocol": self.protocol,
            "base_url": self.base_url,
            "model": self.model,
            "is_local": self.is_local,
            "has_api_key": bool(self.api_key),
            "request_options": dict(self.extra_body),
        }


def normalize_lmstudio_base_url(value: Any) -> str:
    """Return LM Studio's OpenAI-compatible API root exactly once."""
    base_url = str(value or "http://127.0.0.1:1234/v1").strip().rstrip("/")
    return base_url if base_url.endswith("/v1") else f"{base_url}/v1"


def resolve_chat_connection(
    settings: Any,
    overrides: Optional[Mapping[str, Any]] = None,
    *,
    fallback_settings: Any = None,
    require_model: bool = True,
) -> ModelConnectionProfile:
    """Resolve one chat connection from a single configuration snapshot.

    Overrides exist only for unsaved administration-form checks. Runtime callers
    pass no overrides. Unknown providers, missing credentials, endpoints, and
    models fail explicitly; this resolver never falls back to another provider.
    """
    provider = _canonical_provider(
        _setting_value("LLM_PROVIDER", settings, overrides, fallback_settings, "ollama")
    )
    if provider not in SUPPORTED_CHAT_PROVIDERS:
        raise ModelConnectionError(
            f"Unsupported chat provider: {provider or '(empty)'}.",
            "AI_PROVIDER_NOT_SUPPORTED",
        )
    model = _setting_value("CHAT_MODEL", settings, overrides, fallback_settings)
    if require_model and not model:
        raise ModelConnectionError("Select a chat model before calling AI.", "AI_MODEL_REQUIRED")

    ollama_url = _setting_value(
        "OLLAMA_BASE_URL", settings, overrides, fallback_settings, "http://localhost:11434"
    ).rstrip("/")
    openai_url = _setting_value("OPENAI_BASE_URL", settings, overrides, fallback_settings).rstrip("/")
    openai_key = _setting_value("OPENAI_API_KEY", settings, overrides, fallback_settings)
    google_key = _setting_value("GOOGLE_API_KEY", settings, overrides, fallback_settings)

    if provider == "ollama":
        return ModelConnectionProfile("chat", provider, "ollama", ollama_url, None, model, True)
    if provider == "lmstudio":
        return ModelConnectionProfile(
            "chat", provider, "openai", normalize_lmstudio_base_url(openai_url),
            "lm-studio", model, True,
            {"chat_template_kwargs": {"enable_thinking": False}},
        )
    if provider == "gemini":
        _require_value(google_key, "GOOGLE_API_KEY", "AI_CREDENTIAL_REQUIRED")
        return ModelConnectionProfile("chat", provider, "gemini", None, google_key, model, False)

    _require_value(openai_key, "OPENAI_API_KEY", "AI_CREDENTIAL_REQUIRED")
    if provider == "openai":
        base_url = openai_url or "https://api.openai.com/v1"
    elif provider == "deepseek":
        base_url = openai_url or "https://api.deepseek.com/v1"
    else:
        _require_value(openai_url, "OPENAI_BASE_URL", "AI_ENDPOINT_REQUIRED")
        base_url = openai_url
    return ModelConnectionProfile("chat", provider, "openai", base_url, openai_key, model, False)


def resolve_embedding_connection(
    settings: Any,
    overrides: Optional[Mapping[str, Any]] = None,
    *,
    fallback_settings: Any = None,
    require_model: bool = True,
) -> ModelConnectionProfile:
    """Resolve embeddings without assuming every chat endpoint supports them.

    LM Studio may serve chat completions but does not promise a compatible
    embeddings endpoint. It is therefore not an implicit embedding provider.
    """
    provider = _canonical_provider(
        _setting_value("EMBEDDING_PROVIDER", settings, overrides, fallback_settings, "ollama")
    )
    if provider not in SUPPORTED_EMBEDDING_PROVIDERS:
        raise ModelConnectionError(
            f"Unsupported embedding provider: {provider or '(empty)'}.",
            "AI_EMBEDDING_PROVIDER_NOT_SUPPORTED",
        )
    model = _setting_value("EMBEDDING_MODEL", settings, overrides, fallback_settings)
    if require_model and not model:
        raise ModelConnectionError(
            "Select an embedding model before indexing knowledge.",
            "AI_EMBEDDING_MODEL_REQUIRED",
        )
    if provider == "ollama":
        base_url = _setting_value(
            "OLLAMA_BASE_URL", settings, overrides, fallback_settings, "http://localhost:11434"
        ).rstrip("/")
        return ModelConnectionProfile("embedding", provider, "ollama", base_url, None, model, True)

    api_key = _setting_value("OPENAI_API_KEY", settings, overrides, fallback_settings)
    _require_value(api_key, "OPENAI_API_KEY", "AI_CREDENTIAL_REQUIRED")
    base_url = _setting_value("OPENAI_BASE_URL", settings, overrides, fallback_settings).rstrip("/")
    return ModelConnectionProfile(
        "embedding", provider, "openai", base_url or "https://api.openai.com/v1", api_key, model, False
    )


def _canonical_provider(value: Any) -> str:
    provider = str(value or "").strip().lower()
    return _PROVIDER_ALIASES.get(provider, provider)


def _setting_value(
    name: str,
    settings: Any,
    overrides: Optional[Mapping[str, Any]],
    fallback_settings: Any,
    default: str = "",
) -> str:
    if overrides:
        for field, mapped_name in _FORM_FIELD_TO_SETTING.items():
            if mapped_name == name and overrides.get(field) is not None:
                return str(overrides.get(field) or "").strip()
        if overrides.get(name) is not None:
            return str(overrides.get(name) or "").strip()
    value = getattr(settings, name, None)
    if value is None and fallback_settings is not None:
        value = getattr(fallback_settings, name, None)
    return str(default if value is None else value).strip()


def _require_value(value: str, setting_name: str, code: str) -> None:
    if value:
        return
    raise ModelConnectionError(f"Missing required configuration: {setting_name}.", code)
