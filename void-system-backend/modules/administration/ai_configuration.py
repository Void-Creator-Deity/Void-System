"""AI connection configuration behind a small administration interface."""

from __future__ import annotations

import json
import logging
import os
from copy import copy
from dataclasses import is_dataclass, replace
from threading import RLock
import re
import shlex
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Protocol, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from core.model_connection_profile import (
    ModelConnectionError,
    ModelConnectionProfile,
    SUPPORTED_CHAT_PROVIDERS,
    normalize_lmstudio_base_url,
    resolve_chat_connection,
)


logger = logging.getLogger("void-system.administration")

KNOWN_PROVIDERS = set(SUPPORTED_CHAT_PROVIDERS)
CONFIG_FIELD_MAP = {
    "llm_provider": "LLM_PROVIDER",
    "embedding_provider": "EMBEDDING_PROVIDER",
    "ollama_base_url": "OLLAMA_BASE_URL",
    "chat_model": "CHAT_MODEL",
    "embedding_model": "EMBEDDING_MODEL",
    "openai_base_url": "OPENAI_BASE_URL",
    "openai_api_key": "OPENAI_API_KEY",
    "google_api_key": "GOOGLE_API_KEY",
}
MANAGED_ENV_KEYS = frozenset(CONFIG_FIELD_MAP.values())
ALLOWED_EXTRA_PREFIXES = (
    "AI_",
    "OLLAMA_",
    "OPENAI_",
    "GOOGLE_",
    "GEMINI_",
    "DEEPSEEK_",
    "AZURE_OPENAI_",
    "ANTHROPIC_",
    "DASHSCOPE_",
)
SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")


AIConfigurationError = ModelConnectionError


class AIConnectionProbe(Protocol):
    """External model service checks used by AI configuration."""

    def list_ollama_models(self, base_url: str) -> List[str]: ...
    def list_openai_models(self, base_url: str, api_key: str) -> List[str]: ...
    def list_gemini_models(self, api_key: str) -> List[str]: ...
    def verify_ollama_chat(self, base_url: str, model: str) -> None: ...
    def verify_openai_chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        local: bool = False,
        request_body_options: Mapping[str, Any] | None = None,
    ) -> None: ...


class HTTPAIConnectionProbe:
    """HTTP adapter for supported model providers."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds

    def _read_json(self, request: Request) -> Any:
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_ollama_models(self, base_url: str) -> List[str]:
        base = (base_url or "http://localhost:11434").rstrip("/")
        data = self._read_json(Request(f"{base}/api/tags", method="GET"))
        rows = data.get("models") if isinstance(data, dict) else []
        return [str(row["name"]) for row in rows or [] if isinstance(row, dict) and row.get("name")]

    def list_openai_models(self, base_url: str, api_key: str) -> List[str]:
        base = base_url.rstrip("/")
        request = Request(f"{base}/models", headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"}, method="GET")
        data = self._read_json(request)
        rows = data.get("data") if isinstance(data, dict) else []
        return [str(row["id"]) for row in rows or [] if isinstance(row, dict) and row.get("id")]

    def list_gemini_models(self, api_key: str) -> List[str]:
        request = Request("https://generativelanguage.googleapis.com/v1beta/models?key=" + quote(api_key), headers={"Accept": "application/json"}, method="GET")
        data = self._read_json(request)
        rows = data.get("models") if isinstance(data, dict) else []
        return [str(row["name"]).removeprefix("models/") for row in rows or [] if isinstance(row, dict) and row.get("name")]

    def verify_ollama_chat(self, base_url: str, model: str) -> None:
        base = (base_url or "http://localhost:11434").rstrip("/")
        request = Request(
            f"{base}/api/chat",
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "Reply with OK."}],
                "stream": False,
                "options": {"temperature": 0, "num_predict": 64},
            }).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        data = self._read_json(request)
        content = ((data.get("message") or {}).get("content") if isinstance(data, dict) else "") or ""
        if not str(content).strip():
            raise AIConfigurationError("Model returned no visible chat text.", "AI_CHAT_TEST_FAILED")

    def verify_openai_chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        local: bool = False,
        request_body_options: Mapping[str, Any] | None = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "temperature": 0,
            "max_tokens": 64,
            "stream": False,
        }
        if request_body_options:
            payload.update(dict(request_body_options))
        elif local:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        request = Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        data = self._read_json(request)
        choices = data.get("choices") if isinstance(data, dict) else None
        choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        if str(choice.get("finish_reason") or "") == "length":
            raise AIConfigurationError("Model test response was truncated.", "AI_CHAT_TEST_TRUNCATED")
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        content = message.get("content") or ""
        if isinstance(content, list):
            content = "".join(str(item.get("text") or "") for item in content if isinstance(item, dict))
        if str(content).strip():
            return

        streaming_payload = dict(payload)
        streaming_payload["stream"] = True
        streaming_request = Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=json.dumps(streaming_payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "text/event-stream"},
            method="POST",
        )
        streamed_text: List[str] = []
        with urlopen(streaming_request, timeout=self.timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                try:
                    event = json.loads(line[6:])
                except ValueError:
                    continue
                choices = event.get("choices") if isinstance(event, dict) else None
                choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
                delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
                delta_content = delta.get("content") or ""
                if isinstance(delta_content, list):
                    delta_content = "".join(str(item.get("text") or "") for item in delta_content if isinstance(item, dict))
                if str(delta_content):
                    streamed_text.append(str(delta_content))
        if not "".join(streamed_text).strip():
            raise AIConfigurationError("Model returned no visible chat text.", "AI_CHAT_TEST_FAILED")


class AIConfigurationManager:
    """Read, update, and verify the Growth App's AI connection profile."""

    def __init__(
        self,
        env_path: Path,
        runtime_config: Any,
        probe: AIConnectionProbe | None = None,
        runtime_update_callback: Callable[[Any], None] | None = None,
    ) -> None:
        self.env_path = env_path
        self.runtime_config = runtime_config
        self.probe = probe or HTTPAIConnectionProbe()
        self.runtime_update_callback = runtime_update_callback
        self._update_lock = RLock()

    def warn_malformed_env_lines(self) -> None:
        bad_lines = self._find_malformed_env_lines()
        if bad_lines:
            logger.warning("AI configuration file has malformed lines: %s", bad_lines)

    def read_profile(self) -> Dict[str, Any]:
        """Return the saved runtime profile without contacting an upstream service.

        Callers: the administrator configuration page on first load.
        Input: the application-owned RuntimeSettings snapshot.
        Output: credential-safe profile fields only. Model discovery is deliberately
        separate so an unavailable upstream cannot make saved settings appear lost.
        """
        provider = str(getattr(self.runtime_config, "LLM_PROVIDER", "ollama") or "ollama").lower()
        return {
            "llm_provider": provider,
            "embedding_provider": str(getattr(self.runtime_config, "EMBEDDING_PROVIDER", "ollama") or "ollama"),
            "ollama_base_url": str(getattr(self.runtime_config, "OLLAMA_BASE_URL", "") or ""),
            "chat_model": str(getattr(self.runtime_config, "CHAT_MODEL", "") or ""),
            "embedding_model": str(getattr(self.runtime_config, "EMBEDDING_MODEL", "") or ""),
            "openai_base_url": str(getattr(self.runtime_config, "OPENAI_BASE_URL", "") or ""),
            "openai_api_key_set": bool(getattr(self.runtime_config, "OPENAI_API_KEY", None)),
            "google_api_key_set": bool(getattr(self.runtime_config, "GOOGLE_API_KEY", None)),
            "env_entries": self._public_env_entries(),
            "model_options": [],
            "model_options_error": "",
            "supported_providers": sorted(KNOWN_PROVIDERS),
        }

    def update_profile(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        # Persisted environment edits and the runtime snapshot swap must be one
        # administration transaction. Existing requests keep their old immutable
        # snapshot; later requests observe the fully updated one.
        with self._update_lock:
            return self._update_profile_locked(values)

    def _update_profile_locked(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        update_map: Dict[str, str] = {}
        for field_name, env_key in CONFIG_FIELD_MAP.items():
            if values.get(field_name) is None:
                continue
            update_map[env_key] = str(values.get(field_name) or "").strip()

        provider = update_map.get("LLM_PROVIDER")
        if provider and provider.lower() not in KNOWN_PROVIDERS:
            raise AIConfigurationError("暂不支持这个模型来源，请选择列表中的连接方式。")

        if str(update_map.get("LLM_PROVIDER") or "").lower() == "lmstudio":
            update_map["OPENAI_BASE_URL"] = normalize_lmstudio_base_url(
                update_map.get("OPENAI_BASE_URL")
                or getattr(self.runtime_config, "OPENAI_BASE_URL", "")
            )

        extra_env = values.get("extra_env")
        if isinstance(extra_env, Mapping):
            for raw_key, raw_value in extra_env.items():
                key = str(raw_key or "").strip().upper()
                if not self._is_allowed_extra_key(key):
                    raise AIConfigurationError(f"高级配置项 {key or '(空)'} 不在允许范围内。")
                update_map[key] = str(raw_value or "").strip()

        if not update_map:
            return {"updated_keys": [], "persist_to_env": False, "apply_runtime": False}

        persist = bool(values.get("persist_to_env", True))
        apply_runtime = bool(values.get("apply_runtime", True))
        if persist:
            self._upsert_env_values(update_map)
        if apply_runtime:
            self._apply_runtime(update_map)

        logger.info("Administrator updated AI connection keys: %s", sorted(update_map))
        return {
            "updated_keys": sorted(update_map),
            "persist_to_env": persist,
            "apply_runtime": apply_runtime,
        }

    def _connection_profile(
        self,
        values: Mapping[str, Any],
        *,
        require_model: bool,
    ) -> ModelConnectionProfile:
        """Resolve form values against the same runtime profile used by AI calls.

        Unpersisted administrator form values are accepted only for discovery and
        verification. Saving still happens through update_profile; runtime calls
        always resolve the application-owned RuntimeSettings instance.
        """
        return resolve_chat_connection(
            self.runtime_config,
            values,
            require_model=require_model,
        )

    def test_profile(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        """Verify discovery and one visible chat response using one profile.

        A successful result means the selected model and protocol options are
        exactly those that get_chat_llm will use after the same values are saved.
        """
        started = time.perf_counter()
        try:
            profile = self._connection_profile(values, require_model=True)
            models = self._probe_provider(profile)
            if models and profile.model not in models:
                raise AIConfigurationError(
                    f"Connection succeeded but model '{profile.model}' was not discovered.",
                    "AI_MODEL_NOT_FOUND",
                )
            self._verify_chat_generation(profile)
        except AIConfigurationError:
            raise
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            raise AIConfigurationError(
                f"Unable to verify model generation: {self._connection_error_message(exc)}",
                "AI_CHAT_TEST_FAILED",
            ) from exc
        return {
            "provider": profile.provider,
            "model_count": len(models),
            "selected_model_available": not models or profile.model in models,
            "model_options": models,
            "chat_generation_verified": True,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "runtime_profile": profile.public_diagnostics(),
        }

    def discover_models(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        """List upstream models using the canonical, credential-safe profile."""
        try:
            profile = self._connection_profile(values, require_model=False)
            models = self._probe_provider(profile)
        except AIConfigurationError:
            raise
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            raise AIConfigurationError(
                f"Unable to discover upstream models: {self._connection_error_message(exc)}",
                "AI_MODEL_DISCOVERY_FAILED",
            ) from exc
        return {
            "provider": profile.provider,
            "model_options": models,
            "model_count": len(models),
            "runtime_profile": profile.public_diagnostics(),
        }

    def _verify_chat_generation(self, profile: ModelConnectionProfile) -> None:
        if profile.protocol == "ollama":
            self.probe.verify_ollama_chat(profile.base_url or "http://localhost:11434", profile.model)
            return
        if profile.protocol == "openai":
            self.probe.verify_openai_chat(
                profile.base_url or "",
                profile.api_key or "",
                profile.model,
                local=profile.is_local,
                request_body_options=profile.request_body_options,
            )
            return
        raise AIConfigurationError(
            "Gemini connection verification is not implemented by this HTTP probe.",
            "AI_CHAT_TEST_NOT_SUPPORTED",
        )

    def _probe_provider(self, profile: ModelConnectionProfile) -> List[str]:
        if profile.protocol == "ollama":
            return self.probe.list_ollama_models(profile.base_url or "http://localhost:11434")
        if profile.protocol == "openai":
            return self.probe.list_openai_models(profile.base_url or "", profile.api_key or "")
        if profile.protocol == "gemini":
            return self.probe.list_gemini_models(profile.api_key or "")
        raise AIConfigurationError(
            f"Unsupported discovery protocol: {profile.protocol}.",
            "AI_PROTOCOL_NOT_SUPPORTED",
        )

    def _find_malformed_env_lines(self) -> List[int]:
        if not self.env_path.exists():
            return []
        bad_lines: List[int] = []
        for index, raw in enumerate(self.env_path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                bad_lines.append(index)
                continue
            key, value = line.split("=", 1)
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key.strip()):
                bad_lines.append(index)
                continue
            value = value.strip()
            if value and value[0] == value[-1] and value[0] in {"'", '"'}:
                continue
            if value.count('"') % 2 or value.count("'") % 2:
                bad_lines.append(index)
                continue
            try:
                shlex.split(value)
            except ValueError:
                bad_lines.append(index)
        return bad_lines

    def _read_env_pairs(self) -> List[Tuple[str, str]]:
        if not self.env_path.exists():
            return []
        pairs: List[Tuple[str, str]] = []
        for raw in self.env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().upper()
            if key:
                pairs.append((key, value.strip().strip('"').strip("'")))
        return pairs

    def _public_env_entries(self) -> List[Dict[str, str]]:
        return [
            {"key": key, "value": self._mask_value(key, value)}
            for key, value in self._read_env_pairs()
            if key in MANAGED_ENV_KEYS or self._is_allowed_extra_key(key)
        ]

    def _upsert_env_values(self, updates: Mapping[str, str]) -> None:
        lines = self.env_path.read_text(encoding="utf-8", errors="ignore").splitlines() if self.env_path.exists() else []
        pending = dict(updates)
        output: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                output.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            if key in pending:
                output.append(f"{key}={self._serialize_env_value(pending.pop(key))}")
            else:
                output.append(line)
        output.extend(f"{key}={self._serialize_env_value(value)}" for key, value in pending.items())
        self.env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")

    def _apply_runtime(self, updates: Mapping[str, str]) -> None:
        """Publish a complete RuntimeSettings replacement after one config save.

        The prior settings object is never mutated. Requests and workers that
        already captured it can finish consistently, while the callback makes
        the new snapshot authoritative for subsequent dependency resolution.
        """
        next_runtime = replace(self.runtime_config) if is_dataclass(self.runtime_config) else copy(self.runtime_config)
        for key, value in updates.items():
            setattr(next_runtime, key, value)
            os.environ[key] = value
        self.runtime_config = next_runtime
        if self.runtime_update_callback is not None:
            self.runtime_update_callback(next_runtime)

    @staticmethod
    def _serialize_env_value(value: str) -> str:
        if value == "":
            return ""
        if not any(character.isspace() for character in value) and "#" not in value and '"' not in value:
            return value
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    @staticmethod
    def _mask_value(key: str, value: str) -> str:
        if any(marker in key.upper() for marker in SECRET_MARKERS):
            if not value:
                return ""
            return "已配置" if len(value) <= 6 else f"{value[:3]}***{value[-2:]}"
        return value

    @staticmethod
    def _is_allowed_extra_key(key: str) -> bool:
        return bool(re.fullmatch(r"[A-Z_][A-Z0-9_]*", key)) and key not in MANAGED_ENV_KEYS and key.startswith(ALLOWED_EXTRA_PREFIXES)

    @staticmethod
    def _connection_error_message(exc: Exception) -> str:
        if isinstance(exc, HTTPError):
            return f"服务返回 HTTP {exc.code}"
        if isinstance(exc, URLError):
            return str(exc.reason)
        return str(exc) or exc.__class__.__name__
