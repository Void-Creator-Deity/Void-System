"""Regression tests for the single runtime-settings configuration source."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from errors import VoidSystemException
from tools.utils import ALLOWED_FILE_EXTENSIONS, is_allowed_file, validate_file_size


def test_upload_policy_is_not_a_runtime_config_source() -> None:
    assert "pdf" in ALLOWED_FILE_EXTENSIONS
    assert is_allowed_file("brief.pdf")
    assert not is_allowed_file("archive.exe")


def test_file_size_validation_accepts_an_explicit_runtime_limit() -> None:
    validate_file_size(8, max_file_size=8)
    with pytest.raises(VoidSystemException):
        validate_file_size(9, max_file_size=8)


def test_production_source_has_no_legacy_config_imports() -> None:
    source_roots = ("adapters", "api", "core", "middleware", "modules", "services", "tools")
    disallowed_imports = ("from config import config", "from config import Config")
    for root_name in source_roots:
        for source_path in (BACKEND_ROOT / root_name).rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            assert not any(item in source for item in disallowed_imports), source_path

def test_runtime_settings_does_not_keep_retired_infrastructure_knobs() -> None:
    retired_fields = (
        "DATABASE_POOL_SIZE",
        "VECTOR_DIMENSION",
        "LOG_FILE",
        "MAX_CONCURRENT_TASKS",
        "TASK_QUEUE_SIZE",
        "REDIS_URL",
        "CACHE_EXPIRE_SECONDS",
    )
    from core.runtime_settings import RuntimeSettings

    assert all(not hasattr(RuntimeSettings, field) for field in retired_fields)
