"""Small ordered migration runner for the embedded SQLite store."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from typing import Callable, Iterable, Sequence


MigrationAction = Callable[[sqlite3.Connection], None]


class SchemaCompatibilityError(RuntimeError):
    """Raised when a database migration history does not match this runtime."""


@dataclass(frozen=True)
class SchemaState:
    expected_version: int
    actual_version: int
    migration_count: int


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: MigrationAction


def _ordered_migrations(migrations: Iterable[Migration]) -> tuple[Migration, ...]:
    ordered = tuple(sorted(migrations, key=lambda migration: migration.version))
    versions = [migration.version for migration in ordered]
    if len(versions) != len(set(versions)):
        raise ValueError("Migration versions must be unique")
    if versions != list(range(1, len(versions) + 1)):
        raise ValueError("Migration versions must form a contiguous sequence starting at 1")
    return ordered


def inspect_schema(
    connection: sqlite3.Connection,
    migrations: Sequence[Migration],
    *,
    require_latest: bool,
) -> SchemaState:
    """Validate the recorded migration prefix against this runtime's schema contract."""
    ordered = _ordered_migrations(migrations)
    recorded = connection.execute(
        "SELECT version, name FROM schema_migrations ORDER BY version"
    ).fetchall()
    expected_prefix = [(migration.version, migration.name) for migration in ordered[: len(recorded)]]
    recorded_history = [(int(row[0]), str(row[1])) for row in recorded]
    if recorded_history != expected_prefix:
        raise SchemaCompatibilityError(
            "Database migration history does not match this runtime: "
            f"recorded={recorded_history!r}, expected_prefix={expected_prefix!r}"
        )

    expected_version = ordered[-1].version if ordered else 0
    actual_version = recorded_history[-1][0] if recorded_history else 0
    if require_latest and actual_version != expected_version:
        raise SchemaCompatibilityError(
            f"Database schema is at version {actual_version}; runtime requires {expected_version}"
        )
    return SchemaState(
        expected_version=expected_version,
        actual_version=actual_version,
        migration_count=len(recorded_history),
    )


def run_migrations(
    connection_factory: Callable[[], sqlite3.Connection],
    migrations: Iterable[Migration],
) -> SchemaState:
    ordered = _ordered_migrations(migrations)
    connection = connection_factory()
    try:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                   version INTEGER PRIMARY KEY,
                   name TEXT NOT NULL,
                   applied_at TEXT NOT NULL
               )"""
        )
        connection.commit()
        state = inspect_schema(connection, ordered, require_latest=False)
        for migration in ordered[state.migration_count :]:
            try:
                connection.execute("BEGIN IMMEDIATE")
                migration.apply(connection)
                connection.execute(
                    """INSERT INTO schema_migrations (version, name, applied_at)
                       VALUES (?, ?, ?)""",
                    (
                        migration.version,
                        migration.name,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return inspect_schema(connection, ordered, require_latest=True)
    finally:
        connection.close()
