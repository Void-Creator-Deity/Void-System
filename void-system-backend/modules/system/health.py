"""Health-check use case kept outside HTTP routing."""
from __future__ import annotations

from typing import Any, Callable, Dict


class SystemHealth:
    def __init__(self, inspect_database: Callable[[], Any]) -> None:
        self._inspect_database = inspect_database

    def inspect(self) -> Dict[str, Any]:
        state = self._inspect_database()
        return {
            "database": "healthy",
            "schema": "compatible",
            "schema_version": int(state.actual_version),
            "expected_schema_version": int(state.expected_version),
        }
