"""Compatibility import for the retired Database-backed task adapter."""
from adapters.sqlite.task_repository import SQLiteTaskRepository


class LegacyTaskRepository(SQLiteTaskRepository):
    """Deprecated alias accepting the former Database constructor argument."""

    def __init__(self, database) -> None:
        super().__init__(database.get_connection)
