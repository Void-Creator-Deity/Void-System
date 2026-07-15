"""Health-check use case kept outside HTTP routing."""
from __future__ import annotations

from typing import Callable


class SystemHealth:
    def __init__(self, test_database_connection: Callable[[], bool]) -> None:
        self._test_database_connection = test_database_connection

    def database_is_healthy(self) -> bool:
        return bool(self._test_database_connection())
