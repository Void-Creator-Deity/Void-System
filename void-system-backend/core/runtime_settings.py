"""Typed runtime configuration for a composable Void System application."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import secrets
from typing import Mapping, Optional


_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _bool(values: Mapping[str, str], key: str, default: bool) -> bool:
    return values.get(key, str(default)).strip().lower() == "true"


def _int(values: Mapping[str, str], key: str, default: int) -> int:
    raw = values.get(key)
    return default if raw is None or raw.strip() == "" else int(raw)


DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
)


def _origins(values: Mapping[str, str]) -> list[str]:
    raw = values.get("CORS_ORIGINS")
    if raw is None:
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass
class RuntimeSettings:
    """One runtime's configuration, validation, and resolved storage paths.

    The object is deliberately mutable only for the administrator-managed AI
    connection profile. Application composition creates and owns an instance;
    modules receive it through dependencies instead of importing environment
    state during startup.
    """

    BASE_DIR: Path = field(default_factory=lambda: _BACKEND_ROOT)
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    RELOAD: bool = False
    DATABASE_URL: str = "sqlite:///void_system.db"
    DATABASE_POOL_SIZE: int = 10
    SECRET_KEY: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BOOTSTRAP_ADMIN_ENABLED: bool = False
    DEFAULT_ADMIN_USERNAME: str = ""
    DEFAULT_ADMIN_EMAIL: str = ""
    DEFAULT_ADMIN_PASSWORD: str = ""
    ENABLE_TEST_USER_ENDPOINT: bool = False
    ENABLE_LANGSERVE_ROUTES: bool = False
    MAX_FILE_SIZE: int = 52_428_800
    USER_FILES_DIR: str = "user_files"
    LLM_PROVIDER: str = "ollama"
    EMBEDDING_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    CHAT_MODEL: str = "hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M"
    EMBEDDING_MODEL: str = "hf.co/Qwen/Qwen3-Embedding-4B-GGUF:Q8_0"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    CHROMA_PERSIST_DIR: str = "chroma_db"
    VECTOR_DIMENSION: int = 384
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/void_system.log"
    CORS_ORIGINS: list[str] = field(default_factory=lambda: list(DEFAULT_CORS_ORIGINS))
    MAX_CONCURRENT_TASKS: int = 10
    TASK_QUEUE_SIZE: int = 100
    REDIS_URL: Optional[str] = None
    CACHE_EXPIRE_SECONDS: int = 3600

    @classmethod
    def from_environment(
        cls,
        values: Optional[Mapping[str, str]] = None,
        *,
        base_dir: Optional[Path] = None,
    ) -> "RuntimeSettings":
        """Construct settings from an explicit mapping or the process environment."""
        source = os.environ if values is None else values
        return cls(
            BASE_DIR=base_dir or _BACKEND_ROOT,
            ENVIRONMENT=source.get("ENVIRONMENT", "development"),
            HOST=source.get("HOST", "0.0.0.0"),
            PORT=_int(source, "PORT", 8000),
            DEBUG=_bool(source, "DEBUG", True),
            RELOAD=_bool(source, "RELOAD", False),
            DATABASE_URL=source.get("DATABASE_URL", "sqlite:///void_system.db"),
            DATABASE_POOL_SIZE=_int(source, "DATABASE_POOL_SIZE", 10),
            SECRET_KEY=source.get("SECRET_KEY") or secrets.token_urlsafe(32),
            ALGORITHM=source.get("ALGORITHM", "HS256"),
            ACCESS_TOKEN_EXPIRE_MINUTES=_int(source, "ACCESS_TOKEN_EXPIRE_MINUTES", 30),
            REFRESH_TOKEN_EXPIRE_DAYS=_int(source, "REFRESH_TOKEN_EXPIRE_DAYS", 7),
            BOOTSTRAP_ADMIN_ENABLED=_bool(source, "BOOTSTRAP_ADMIN_ENABLED", False),
            DEFAULT_ADMIN_USERNAME=source.get("DEFAULT_ADMIN_USERNAME", ""),
            DEFAULT_ADMIN_EMAIL=source.get("DEFAULT_ADMIN_EMAIL", ""),
            DEFAULT_ADMIN_PASSWORD=source.get("DEFAULT_ADMIN_PASSWORD", ""),
            ENABLE_TEST_USER_ENDPOINT=_bool(source, "ENABLE_TEST_USER_ENDPOINT", False),
            ENABLE_LANGSERVE_ROUTES=_bool(source, "ENABLE_LANGSERVE_ROUTES", False),
            MAX_FILE_SIZE=_int(source, "MAX_FILE_SIZE", 52_428_800),
            USER_FILES_DIR=source.get("USER_FILES_DIR", "user_files"),
            LLM_PROVIDER=source.get("LLM_PROVIDER", "ollama"),
            EMBEDDING_PROVIDER=source.get("EMBEDDING_PROVIDER", "ollama"),
            OLLAMA_BASE_URL=source.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            CHAT_MODEL=source.get("CHAT_MODEL", "hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M"),
            EMBEDDING_MODEL=source.get("EMBEDDING_MODEL", "hf.co/Qwen/Qwen3-Embedding-4B-GGUF:Q8_0"),
            OPENAI_API_KEY=source.get("OPENAI_API_KEY") or None,
            OPENAI_BASE_URL=source.get("OPENAI_BASE_URL") or None,
            GOOGLE_API_KEY=source.get("GOOGLE_API_KEY") or None,
            CHROMA_PERSIST_DIR=source.get("CHROMA_PERSIST_DIR", "chroma_db"),
            VECTOR_DIMENSION=_int(source, "VECTOR_DIMENSION", 384),
            LOG_LEVEL=source.get("LOG_LEVEL", "INFO"),
            LOG_FILE=source.get("LOG_FILE", "logs/void_system.log"),
            CORS_ORIGINS=_origins(source),
            MAX_CONCURRENT_TASKS=_int(source, "MAX_CONCURRENT_TASKS", 10),
            TASK_QUEUE_SIZE=_int(source, "TASK_QUEUE_SIZE", 100),
            REDIS_URL=source.get("REDIS_URL") or None,
            CACHE_EXPIRE_SECONDS=_int(source, "CACHE_EXPIRE_SECONDS", 3600),
        )

    def validate_runtime(self) -> None:
        """Fail early when a production configuration is unsafe or incomplete."""
        if self.is_production() and len(self.SECRET_KEY) < 32:
            raise RuntimeError("Production SECRET_KEY must contain at least 32 characters")
        if self.is_production() and "*" in self.CORS_ORIGINS:
            raise RuntimeError("Production CORS_ORIGINS cannot contain a wildcard")
        if self.BOOTSTRAP_ADMIN_ENABLED and not all(
            (self.DEFAULT_ADMIN_USERNAME, self.DEFAULT_ADMIN_EMAIL, self.DEFAULT_ADMIN_PASSWORD)
        ):
            raise RuntimeError("BOOTSTRAP_ADMIN_ENABLED requires all DEFAULT_ADMIN_* values")

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    def get_database_path(self) -> str:
        if self.DATABASE_URL.startswith("sqlite:///"):
            return str(self.BASE_DIR / self.DATABASE_URL.removeprefix("sqlite:///"))
        return self.DATABASE_URL

    def get_user_files_path(self) -> Path:
        return self.BASE_DIR / self.USER_FILES_DIR

    def get_chroma_path(self) -> Path:
        return self.BASE_DIR / self.CHROMA_PERSIST_DIR
