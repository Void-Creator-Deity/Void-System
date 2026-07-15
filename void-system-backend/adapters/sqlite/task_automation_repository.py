"""SQLite adapter for Trigger-to-Run automation and durable Run commands."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Mapping, Optional, Sequence


def _now() -> str:
    return datetime.now().isoformat()


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _decode(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    value = dict(row)
    for field in ("configuration", "run_template", "payload"):
        if field in value:
            try:
                value[field] = json.loads(value[field]) if value[field] else {}
            except (TypeError, json.JSONDecodeError):
                value[field] = {}
    return value


class SQLiteTaskAutomationRepository:
    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def create_trigger(self, user_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        trigger_id, now = str(uuid.uuid4()), _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO task_triggers
                   (trigger_id, user_id, goal_id, name, trigger_type, status,
                    configuration, run_template, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)""",
                (trigger_id, user_id, values["goal_id"], values["name"], values["trigger_type"],
                 _json(values.get("configuration")), _json(values["run_template"]), now, now),
            )
            conn.commit()
            return self.get_trigger(user_id, trigger_id) or {}
        finally:
            conn.close()

    def list_triggers(self, user_id: str) -> Sequence[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return [_decode(row) or {} for row in conn.execute(
                "SELECT * FROM task_triggers WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)
            ).fetchall()]
        finally:
            conn.close()

    def get_trigger(self, user_id: str, trigger_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(conn.execute(
                "SELECT * FROM task_triggers WHERE trigger_id = ? AND user_id = ?", (trigger_id, user_id)
            ).fetchone())
        finally:
            conn.close()

    def update_trigger(
        self, user_id: str, trigger_id: str, values: Mapping[str, Any]
    ) -> bool:
        allowed = {"name", "configuration", "run_template"}
        fields = [field for field in allowed if field in values]
        if not fields:
            return False
        assignments = [f"{field} = ?" for field in fields]
        params = [_json(values[field]) if field in {"configuration", "run_template"} else values[field] for field in fields]
        assignments.append("updated_at = ?")
        params.extend((_now(), trigger_id, user_id))
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                f"UPDATE task_triggers SET {', '.join(assignments)} WHERE trigger_id = ? AND user_id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_trigger(self, user_id: str, trigger_id: str) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                "DELETE FROM task_triggers WHERE trigger_id = ? AND user_id = ?",
                (trigger_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def set_trigger_status(self, user_id: str, trigger_id: str, status: str) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                "UPDATE task_triggers SET status = ?, updated_at = ? WHERE trigger_id = ? AND user_id = ?",
                (status, _now(), trigger_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_firing(self, user_id: str, trigger_id: str, source_key: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(conn.execute(
                """SELECT * FROM task_trigger_firings
                   WHERE trigger_id = ? AND user_id = ? AND source_key = ?""",
                (trigger_id, user_id, source_key),
            ).fetchone())
        finally:
            conn.close()

    def record_firing(self, user_id: str, trigger_id: str, source_key: str, run_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        conn, now = self._connection_factory(), _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT * FROM task_trigger_firings WHERE trigger_id = ? AND source_key = ?",
                (trigger_id, source_key),
            ).fetchone()
            if existing is not None:
                conn.rollback()
                return _decode(existing) or {}
            firing_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO task_trigger_firings
                   (firing_id, trigger_id, user_id, source_key, run_id, payload, fired_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (firing_id, trigger_id, user_id, source_key, run_id, _json(payload), now),
            )
            conn.execute(
                "UPDATE task_triggers SET last_fired_at = ?, updated_at = ? WHERE trigger_id = ? AND user_id = ?",
                (now, now, trigger_id, user_id),
            )
            conn.execute(
                """INSERT INTO task_events
                   (event_id, run_id, user_id, event_type, payload, created_at)
                   VALUES (?, ?, ?, 'trigger.fired', ?, ?)""",
                (str(uuid.uuid4()), run_id, user_id,
                 _json({"trigger_id": trigger_id, "source_key": source_key}), now),
            )
            conn.commit()
            return {"firing_id": firing_id, "trigger_id": trigger_id, "user_id": user_id,
                    "source_key": source_key, "run_id": run_id, "payload": dict(payload), "fired_at": now}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_command(self, user_id: str, run_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        conn, now = self._connection_factory(), _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            key = values.get("idempotency_key")
            if key:
                existing = conn.execute(
                    """SELECT * FROM task_run_commands
                       WHERE run_id = ? AND user_id = ? AND idempotency_key = ?""",
                    (run_id, user_id, key),
                ).fetchone()
                if existing is not None:
                    conn.rollback()
                    return _decode(existing) or {}
            command_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO task_run_commands
                   (command_id, run_id, user_id, command_type, instruction, payload,
                    status, idempotency_key, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
                (command_id, run_id, user_id, values["command_type"], values["instruction"],
                 _json(values.get("payload")), key, now),
            )
            conn.execute(
                """INSERT INTO task_events
                   (event_id, run_id, user_id, event_type, payload, created_at)
                   VALUES (?, ?, ?, 'run.command_added', ?, ?)""",
                (str(uuid.uuid4()), run_id, user_id,
                 _json({"command_id": command_id, "command_type": values["command_type"]}), now),
            )
            conn.commit()
            return {"command_id": command_id, "run_id": run_id, "user_id": user_id,
                    "command_type": values["command_type"], "instruction": values["instruction"],
                    "payload": dict(values.get("payload") or {}), "status": "pending",
                    "idempotency_key": key, "created_at": now, "acknowledged_at": None}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_command(self, user_id: str, run_id: str, command_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(conn.execute(
                """SELECT * FROM task_run_commands
                   WHERE command_id = ? AND run_id = ? AND user_id = ?""",
                (command_id, run_id, user_id),
            ).fetchone())
        finally:
            conn.close()

    def list_commands(self, user_id: str, run_id: str, status: Optional[str] = None) -> Sequence[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            if status:
                rows = conn.execute(
                    """SELECT * FROM task_run_commands WHERE run_id = ? AND user_id = ? AND status = ?
                       ORDER BY created_at""", (run_id, user_id, status)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM task_run_commands WHERE run_id = ? AND user_id = ? ORDER BY created_at",
                    (run_id, user_id),
                ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def acknowledge_command(self, user_id: str, run_id: str, command_id: str) -> bool:
        conn, now = self._connection_factory(), _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """UPDATE task_run_commands SET status = 'acknowledged', acknowledged_at = ?
                   WHERE command_id = ? AND run_id = ? AND user_id = ? AND status = 'pending'""",
                (now, command_id, run_id, user_id),
            )
            if cursor.rowcount:
                conn.execute(
                    """INSERT INTO task_events
                       (event_id, run_id, user_id, event_type, payload, created_at)
                       VALUES (?, ?, ?, 'run.command_acknowledged', ?, ?)""",
                    (str(uuid.uuid4()), run_id, user_id, _json({"command_id": command_id}), now),
                )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
