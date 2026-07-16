"""SQLite Adapter implementing the Task Workflow persistence interface."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence

from adapters.sqlite.task_execution_projection import ensure_task_projection, sync_task_status
from core.task_contracts import RewardGrant, TaskRepository


ConnectionFactory = Callable[[], sqlite3.Connection]
_JSON_OBJECT_FIELDS = ("related_attrs", "proof_data", "self_evaluation", "ai_suggestion")


class SQLiteTaskRepository(TaskRepository):
    """Keep task lifecycle persistence and atomic settlement in one Adapter."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _decode_task(row: sqlite3.Row) -> Dict[str, Any]:
        task = dict(row)
        for field in _JSON_OBJECT_FIELDS:
            raw = task.get(field)
            try:
                task[field] = json.loads(raw) if raw else {}
            except (TypeError, json.JSONDecodeError):
                task[field] = {}
        raw_prerequisites = task.get("prerequisites")
        try:
            task["prerequisites"] = json.loads(raw_prerequisites) if raw_prerequisites else []
        except (TypeError, json.JSONDecodeError):
            task["prerequisites"] = []
        return task

    def get_task(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            ).fetchone()
            return self._decode_task(row) if row is not None else None
        finally:
            conn.close()

    def list_tasks(self, user_id: str) -> Sequence[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [self._decode_task(row) for row in rows]
        finally:
            conn.close()

    def list_attributes(self, user_id: str) -> List[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM attributes WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def update_status(self, user_id: str, task_id: str, status: str) -> bool:
        conn = self._connection_factory()
        now = datetime.now().isoformat()
        try:
            conn.execute("BEGIN IMMEDIATE")
            task = conn.execute(
                "SELECT 1 FROM tasks WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            ).fetchone()
            if task is None:
                conn.rollback()
                return False
            if ensure_task_projection(conn, user_id, task_id, now) is None:
                raise RuntimeError("Task is missing its canonical execution projection")
            sync_task_status(conn, user_id, task_id, status, now)
            if status == "completed":
                conn.execute(
                    """UPDATE tasks SET status = ?, completed_at = COALESCE(completed_at, ?),
                              updated_at = ? WHERE task_id = ? AND user_id = ?""",
                    (status, now, now, task_id, user_id),
                )
            else:
                conn.execute(
                    """UPDATE tasks SET status = ?, completed_at = NULL, updated_at = ?
                       WHERE task_id = ? AND user_id = ?""",
                    (status, now, task_id, user_id),
                )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    def submit_proof(self, user_id: str, task_id: str, proof: Dict[str, Any]) -> bool:
        conn = self._connection_factory()
        now = datetime.now().isoformat()
        try:
            conn.execute("BEGIN IMMEDIATE")
            task = conn.execute(
                "SELECT 1 FROM tasks WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            ).fetchone()
            if task is None:
                conn.rollback()
                return False
            if ensure_task_projection(conn, user_id, task_id, now) is None:
                raise RuntimeError("Task is missing its canonical execution projection")
            sync_task_status(conn, user_id, task_id, "pending_evaluation", now)
            conn.execute(
                """UPDATE tasks SET proof_data = ?, status = 'pending_evaluation', updated_at = ?
                   WHERE task_id = ? AND user_id = ?""",
                (json.dumps(proof), now, task_id, user_id),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    def update_evaluation(
        self,
        user_id: str,
        task_id: str,
        *,
        self_evaluation: Optional[Dict[str, Any]] = None,
        ai_suggestion: Optional[Dict[str, Any]] = None,
    ) -> bool:
        updates: List[str] = []
        params: List[Any] = []
        if self_evaluation is not None:
            updates.append("self_evaluation = ?")
            params.append(json.dumps(self_evaluation))
        if ai_suggestion is not None:
            updates.append("ai_suggestion = ?")
            params.append(json.dumps(ai_suggestion))
        if not updates:
            return False

        conn = self._connection_factory()
        try:
            params.extend((task_id, user_id))
            cursor = conn.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ? AND user_id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def settle_completion(
        self,
        user_id: str,
        task_id: str,
        reward: RewardGrant,
        *,
        ai_suggestion: Optional[Dict[str, Any]] = None,
    ) -> bool:
        conn = self._connection_factory()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                "SELECT status FROM tasks WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            )
            if cursor.fetchone() is None:
                conn.rollback()
                return False
            execution_link = ensure_task_projection(conn, user_id, task_id, now)
            if execution_link is None:
                raise RuntimeError("Task is missing its canonical execution projection")

            cursor.execute(
                "SELECT 1 FROM task_reward_settlements WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            )
            if cursor.fetchone() is not None:
                sync_task_status(conn, user_id, task_id, "completed", now)
                self._mark_completed(cursor, task_id, user_id, now, ai_suggestion, preserve_time=True)
                conn.commit()
                return False

            # Canonical completion is durable before reward compatibility data is materialized.
            sync_task_status(conn, user_id, task_id, "completed", now)
            coins = max(0, int(reward.coins))
            experience = max(0, int(reward.experience))
            increments = reward.attribute_increments or {}
            cursor.execute(
                """INSERT INTO task_reward_settlements
                   (settlement_id, task_id, user_id, run_id, step_id, coins, experience,
                    attribute_increments, source, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), task_id, user_id, execution_link["run_id"],
                    execution_link["step_id"], coins, experience, json.dumps(increments),
                    reward.source, now,
                ),
            )
            if coins > 0:
                cursor.execute(
                    """INSERT INTO coins (record_id, user_id, amount, type, source)
                       VALUES (?, ?, ?, 'earn', ?)""",
                    (str(uuid.uuid4()), user_id, coins, reward.source),
                )
            if experience > 0:
                cursor.execute(
                    "INSERT INTO experience (record_id, user_id, amount, source) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), user_id, experience, reward.source),
                )
                cursor.execute(
                    "UPDATE users SET experience = experience + ? WHERE user_id = ?",
                    (experience, user_id),
                )
            for attr_id, increment in increments.items():
                normalized = max(0, int(increment))
                if normalized <= 0:
                    continue
                cursor.execute(
                    """UPDATE attributes
                       SET attr_value = MIN(max_value, attr_value + ?), updated_at = ?
                       WHERE attr_id = ? AND user_id = ?""",
                    (normalized, now, attr_id, user_id),
                )

            self._mark_completed(cursor, task_id, user_id, now, ai_suggestion)
            if cursor.rowcount <= 0:
                raise RuntimeError("Task disappeared during reward settlement")
            conn.execute(
                """INSERT INTO task_events
                   (event_id, run_id, step_id, user_id, event_type, payload, created_at)
                   VALUES (?, ?, ?, ?, 'reward.settled', ?, ?)""",
                (
                    str(uuid.uuid4()),
                    execution_link["run_id"],
                    execution_link["step_id"],
                    user_id,
                    json.dumps({
                        "coins": coins,
                        "experience": experience,
                        "attribute_increments": increments,
                        "source": reward.source,
                    }),
                    now,
                ),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _mark_completed(
        cursor: sqlite3.Cursor,
        task_id: str,
        user_id: str,
        now: str,
        ai_suggestion: Optional[Dict[str, Any]],
        preserve_time: bool = False,
    ) -> None:
        completed_at = "COALESCE(completed_at, ?)" if preserve_time else "?"
        if ai_suggestion is not None:
            cursor.execute(
                f"""UPDATE tasks SET status = 'completed', ai_suggestion = ?,
                    completed_at = {completed_at}, updated_at = ?
                    WHERE task_id = ? AND user_id = ?""",
                (json.dumps(ai_suggestion), now, now, task_id, user_id),
            )
        else:
            cursor.execute(
                f"""UPDATE tasks SET status = 'completed', completed_at = {completed_at},
                    updated_at = ? WHERE task_id = ? AND user_id = ?""",
                (now, now, task_id, user_id),
            )
