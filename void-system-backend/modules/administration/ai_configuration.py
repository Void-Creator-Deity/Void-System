"""AI connection configuration behind a small administration interface."""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Protocol, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


logger = logging.getLogger("void-system.administration")

KNOWN_PROVIDERS = {"ollama", "openai", "deepseek", "gemini", "openai_compat", "lmstudio"}
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


class AIConfigurationError(Exception):
    """An administration-safe configuration or connection error."""

    def __init__(self, message: str, code: str = "AI_CONFIGURATION_INVALID") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class AIConnectionProbe(Protocol):
    """External model service checks used by AI configuration."""

    def list_ollama_models(self, base_url: str) -> List[str]: ...

    def list_openai_models(self, base_url: str, api_key: str) -> List[str]: ...

    def list_gemini_models(self, api_key: str) -> List[str]: ...


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
        request = Request(
            f"{base}/models",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            method="GET",
        )
        data = self._read_json(request)
        rows = data.get("data") if isinstance(data, dict) else []
        return [str(row["id"]) for row in rows or [] if isinstance(row, dict) and row.get("id")]

    def list_gemini_models(self, api_key: str) -> List[str]:
        request = Request(
            "https://generativelanguage.googleapis.com/v1beta/models?key=" + quote(api_key),
            headers={"Accept": "application/json"},
            method="GET",
        )
        data = self._read_json(request)
        rows = data.get("models") if isinstance(data, dict) else []
        return [
            str(row["name"]).removeprefix("models/")
            for row in rows or []
            if isinstance(row, dict) and row.get("name")
        ]


class AIConfigurationManager:
    """Read, update, and verify the Growth App's AI connection profile."""

    def __init__(
        self,
        env_path: Path,
        config_type: Any,
        runtime_config: Any,
        probe: AIConnectionProbe | None = None,
    ) -> None:
        self.env_path = env_path
        self.config_type = config_type
        self.runtime_config = runtime_config
        self.probe = probe or HTTPAIConnectionProbe()

    def warn_malformed_env_lines(self) -> None:
        bad_lines = self._find_malformed_env_lines()
        if bad_lines:
            logger.warning("AI configuration file has malformed lines: %s", bad_lines)

    def read_profile(self) -> Dict[str, Any]:
        provider = str(getattr(self.config_type, "LLM_PROVIDER", "ollama") or "ollama").lower()
        model_options: List[str] = []
        model_error = ""
        if provider == "ollama":
            try:
                model_options = self.probe.list_ollama_models(
                    str(getattr(self.config_type, "OLLAMA_BASE_URL", "http://localhost:11434"))
                )
            except Exception as exc:
                model_error = self._connection_error_message(exc)
        elif provider == "lmstudio":
            try:
                model_options = self.probe.list_openai_models(
                    str(getattr(self.config_type, "OPENAI_BASE_URL", "") or "http://127.0.0.1:1234/v1"),
                    "lm-studio",
                )
            except Exception as exc:
                model_error = self._connection_error_message(exc)

        return {
            "llm_provider": provider,
            "embedding_provider": str(getattr(self.config_type, "EMBEDDING_PROVIDER", "ollama") or "ollama"),
            "ollama_base_url": str(getattr(self.config_type, "OLLAMA_BASE_URL", "") or ""),
            "chat_model": str(getattr(self.config_type, "CHAT_MODEL", "") or ""),
            "embedding_model": str(getattr(self.config_type, "EMBEDDING_MODEL", "") or ""),
            "openai_base_url": str(getattr(self.config_type, "OPENAI_BASE_URL", "") or ""),
            "openai_api_key_set": bool(getattr(self.config_type, "OPENAI_API_KEY", None)),
            "google_api_key_set": bool(getattr(self.config_type, "GOOGLE_API_KEY", None)),
            "env_entries": self._public_env_entries(),
            "model_options": model_options,
            "model_options_error": model_error,
            "supported_providers": sorted(KNOWN_PROVIDERS),
        }

    def update_profile(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        update_map: Dict[str, str] = {}
        for field_name, env_key in CONFIG_FIELD_MAP.items():
            if values.get(field_name) is None:
                continue
            update_map[env_key] = str(values.get(field_name) or "").strip()

        provider = update_map.get("LLM_PROVIDER")
        if provider and provider.lower() not in KNOWN_PROVIDERS:
            raise AIConfigurationError("暂不支持这个模型来源，请选择列表中的连接方式。")

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

    def test_profile(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        provider = str(values.get("llm_provider") or getattr(self.config_type, "LLM_PROVIDER", "ollama")).strip().lower()
        if provider not in KNOWN_PROVIDERS:
            raise AIConfigurationError("暂不支持这个模型来源。", "AI_PROVIDER_NOT_SUPPORTED")

        started = time.perf_counter()
        try:
            models = self._probe_provider(provider, values)
        except AIConfigurationError:
            raise
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            raise AIConfigurationError(
                f"无法连接到模型服务：{self._connection_error_message(exc)}",
                "AI_CONNECT_TEST_FAILED",
            ) from exc

        model = str(values.get("chat_model") or getattr(self.config_type, "CHAT_MODEL", "") or "").strip()
        if model and models and model not in models:
            raise AIConfigurationError(
                f"连接正常，但没有找到模型“{model}”。请刷新模型列表或更换模型。",
                "AI_MODEL_NOT_FOUND",
            )
        return {
            "provider": provider,
            "model_count": len(models),
            "selected_model_available": not model or not models or model in models,
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }

    def _probe_provider(self, provider: str, values: Mapping[str, Any]) -> List[str]:
        if provider == "ollama":
            base_url = str(values.get("ollama_base_url") or getattr(self.config_type, "OLLAMA_BASE_URL", "http://localhost:11434")).strip()
            return self.probe.list_ollama_models(base_url)
        if provider == "lmstudio":
            base_url = str(
                values.get("openai_base_url")
                or getattr(self.config_type, "OPENAI_BASE_URL", "")
                or "http://127.0.0.1:1234/v1"
            ).strip()
            return self.probe.list_openai_models(base_url, "lm-studio")
        if provider in {"openai", "deepseek", "openai_compat"}:
            api_key = str(values.get("openai_api_key") or getattr(self.config_type, "OPENAI_API_KEY", "") or "").strip()
            if not api_key:
                raise AIConfigurationError("请先填写 API Key。", "AI_CONNECT_TEST_FAILED")
            base_url = str(values.get("openai_base_url") or getattr(self.config_type, "OPENAI_BASE_URL", "") or "").strip()
            if not base_url:
                if provider == "openai":
                    base_url = "https://api.openai.com/v1"
                elif provider == "deepseek":
                    base_url = "https://api.deepseek.com/v1"
                else:
                    raise AIConfigurationError("兼容接口需要填写服务地址。")
            return self.probe.list_openai_models(base_url, api_key)
        api_key = str(values.get("google_api_key") or getattr(self.config_type, "GOOGLE_API_KEY", "") or "").strip()
        if not api_key:
            raise AIConfigurationError("请先填写 Gemini API Key。", "AI_CONNECT_TEST_FAILED")
        return self.probe.list_gemini_models(api_key)

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
        for key, value in updates.items():
            setattr(self.config_type, key, value)
            setattr(self.runtime_config, key, value)
            os.environ[key] = value

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
