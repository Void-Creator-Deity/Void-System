"""Small ordered migration runner for the embedded SQLite store."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from typing import Callable, Iterable


MigrationAction = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: MigrationAction


def run_migrations(
    connection_factory: Callable[[], sqlite3.Connection],
    migrations: Iterable[Migration],
) -> None:
    ordered = sorted(migrations, key=lambda migration: migration.version)
    versions = [migration.version for migration in ordered]
    if len(versions) != len(set(versions)):
        raise ValueError("Migration versions must be unique")

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
        applied = {
            row[0]
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        }
        for migration in ordered:
            if migration.version in applied:
                continue
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
    finally:
        connection.close()
