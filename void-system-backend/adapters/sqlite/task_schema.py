"""Canonical SQLite schema rules for Task Execution object fields."""
from __future__ import annotations

import sqlite3
from typing import Dict, Optional, Tuple

from adapters.sqlite.object_json import encode_legacy_object


ObjectColumnMap = Dict[str, Optional[str]]
TaskObjectContract = Dict[str, Tuple[str, ObjectColumnMap]]


TASK_OBJECT_COLUMNS: TaskObjectContract = {
    "task_goals": ("goal_id", {"metadata": None}),
    "task_runs": ("run_id", {"metadata": None}),
    "task_steps": (
        "step_id",
        {
            "completion_criteria": "criteria",
            "input_data": None,
            "reward_spec": None,
            "output_data": None,
        },
    ),
    "task_actions": (
        "action_id",
        {"input_data": None, "output_data": None},
    ),
    "task_events": ("event_id", {"payload": None}),
    "task_artifacts": ("artifact_id", {"metadata": None}),
    "task_approvals": (
        "approval_id",
        {"request_data": None, "decision_data": None},
    ),
    "task_triggers": (
        "trigger_id",
        {"configuration": None, "run_template": None},
    ),
    "task_trigger_firings": ("firing_id", {"payload": None}),
}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def enforce_task_object_json_contract(conn: sqlite3.Connection) -> None:
    """Normalize history, then reject non-object JSON at every task-domain write path."""
    for table_name, (primary_key, columns) in TASK_OBJECT_COLUMNS.items():
        if not _table_exists(conn, table_name):
            continue
        available_columns = {
            row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        present_columns = {
            column: legacy_text_key
            for column, legacy_text_key in columns.items()
            if column in available_columns
        }
        if not present_columns:
            continue

        selected = ", ".join((primary_key, *present_columns))
        for row in conn.execute(f"SELECT {selected} FROM {table_name}").fetchall():
            for column, legacy_text_key in present_columns.items():
                normalized = encode_legacy_object(
                    row[column], legacy_text_key=legacy_text_key
                )
                if normalized != (row[column] or "{}"):
                    conn.execute(
                        f"UPDATE {table_name} SET {column} = ? WHERE {primary_key} = ?",
                        (normalized, row[primary_key]),
                    )

        invalid_condition = " OR ".join(
            f"CASE WHEN json_valid(NEW.{column}) "
            f"THEN json_type(NEW.{column}) != 'object' ELSE 1 END"
            for column in present_columns
        )
        for operation in ("insert", "update"):
            trigger_name = f"validate_{table_name}_object_json_{operation}"
            conn.execute(
                f"""CREATE TRIGGER IF NOT EXISTS {trigger_name}
                   BEFORE {operation.upper()} ON {table_name}
                   WHEN {invalid_condition}
                   BEGIN
                       SELECT RAISE(ABORT, '{table_name} object fields must contain JSON objects');
                   END"""
            )
