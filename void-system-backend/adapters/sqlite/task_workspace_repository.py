"""SQLite adapter for the task workspace and task catalog module."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence

from adapters.sqlite.task_execution_projection import (
    delete_chain_projection,
    delete_task_projection,
    ensure_task_projection,
    project_chain,
    sync_task_progress,
)
from adapters.sqlite.task_repository import ConnectionFactory, SQLiteTaskRepository
from core.task_workspace_contracts import TaskWorkspaceRepository


class SQLiteTaskWorkspaceRepository(TaskWorkspaceRepository):
    """Own task workspace persistence without exposing the legacy Database facade."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _decode_task(row: sqlite3.Row) -> Dict[str, Any]:
        return SQLiteTaskRepository._decode_task(row)

    def list_attributes(self, user_id: str) -> List[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM attributes WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def create_task(self, user_id: str, values: Mapping[str, Any]) -> str:
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = self._connection_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO tasks
                   (task_id, user_id, category_id, chain_id, chain_order, task_name, description,
                    related_attrs, estimated_time, reward_coins, priority, attribute_points,
                    prerequisites, completion_type, completion_criteria, task_type, is_optional,
                    is_daily, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    user_id,
                    values.get("category_id"),
                    values.get("chain_id"),
                    int(values.get("chain_order") or 0),
                    str(values["task_name"]),
                    str(values.get("description") or ""),
                    json.dumps(values.get("related_attrs") or {}),
                    int(values.get("estimated_time") or 30),
                    int(values.get("reward_coins") if values.get("reward_coins") is not None else 10),
                    str(values.get("priority") or "medium"),
                    int(values.get("attribute_points") or 0),
                    json.dumps(values.get("prerequisites") or []),
                    str(values.get("completion_type") or "simple"),
                    json.dumps(values.get("completion_criteria") or {}),
                    str(values.get("task_type") or "main"),
                    1 if values.get("is_optional") else 0,
                    1 if values.get("is_daily") else 0,
                    now,
                    now,
                ),
            )
            if ensure_task_projection(conn, user_id, task_id, now) is None:
                raise RuntimeError("Task execution projection was not created")
            conn.commit()
            return task_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def list_workspace_tasks(
        self,
        user_id: str,
        *,
        task_status: Optional[str] = None,
        category_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Sequence[Dict[str, Any]]:
        clauses = ["user_id = ?"]
        params: List[Any] = [user_id]
        if task_status:
            clauses.append("status = ?")
            params.append(task_status)
        if category_id:
            clauses.append("category_id = ?")
            params.append(category_id)
        query = "SELECT * FROM tasks WHERE " + " AND ".join(clauses) + " ORDER BY created_at DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        if offset is not None and limit is not None:
            query += " OFFSET ?"
            params.append(offset)
        conn = self._connection_factory()
        try:
            return [self._decode_task(row) for row in conn.execute(query, params).fetchall()]
        finally:
            conn.close()

    def get_workspace_task(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ? AND user_id = ?", (task_id, user_id)
            ).fetchone()
            return self._decode_task(row) if row is not None else None
        finally:
            conn.close()

    def delete_workspace_task(self, user_id: str, task_id: str) -> bool:
        conn = self._connection_factory()
        now = datetime.now().isoformat()
        try:
            conn.execute("BEGIN IMMEDIATE")
            exists = conn.execute(
                "SELECT 1 FROM tasks WHERE task_id = ? AND user_id = ?", (task_id, user_id)
            ).fetchone()
            if exists is None:
                conn.rollback()
                return False
            delete_task_projection(conn, user_id, task_id, now)
            conn.execute(
                "DELETE FROM tasks WHERE task_id = ? AND user_id = ?", (task_id, user_id)
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_task_progress(self, user_id: str, task_id: str, progress: int) -> bool:
        conn = self._connection_factory()
        now = datetime.now().isoformat()
        normalized = max(0, min(100, int(progress)))
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """UPDATE tasks SET current_progress = ?, updated_at = ?
                   WHERE task_id = ? AND user_id = ?""",
                (normalized, now, task_id, user_id),
            )
            if cursor.rowcount > 0:
                sync_task_progress(conn, user_id, task_id, normalized, now)
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def task_statistics(self, user_id: str) -> Dict[str, Any]:
        conn = self._connection_factory()
        try:
            status_rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM tasks WHERE user_id = ? GROUP BY status", (user_id,)
            ).fetchall()
            status_stats = {str(row["status"]): int(row["count"]) for row in status_rows}
            total_tasks = sum(status_stats.values())
            completed_last_30_days = int(conn.execute(
                """SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'completed'
                   AND completed_at >= date('now', '-30 days')""", (user_id,)
            ).fetchone()[0] or 0)
            average = conn.execute(
                "SELECT AVG(estimated_time) FROM tasks WHERE user_id = ? AND status = 'completed'", (user_id,)
            ).fetchone()[0]
            return {
                "total_tasks": total_tasks,
                "status_stats": status_stats,
                "completed_last_30_days": completed_last_30_days,
                "avg_estimated_time": round(float(average or 0), 1),
            }
        finally:
            conn.close()

    def list_categories(self, user_id: str) -> Sequence[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                """SELECT * FROM task_categories WHERE user_id = ?
                   ORDER BY is_preset DESC, created_at DESC""", (user_id,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_category(self, user_id: str, category_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            row = conn.execute(
                "SELECT * FROM task_categories WHERE category_id = ? AND user_id = ?",
                (category_id, user_id),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def create_category(self, user_id: str, values: Mapping[str, Any]) -> str:
        category_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO task_categories
                   (category_id, user_id, category_name, description, icon, color, is_preset, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (
                    category_id, user_id, str(values["category_name"]),
                    str(values.get("description") or ""), str(values.get("icon") or "📁"),
                    str(values.get("color") or "#3B82F6"), now, now,
                ),
            )
            conn.commit()
            return category_id
        finally:
            conn.close()

    def update_category(self, user_id: str, category_id: str, values: Mapping[str, Any]) -> bool:
        fields = ("category_name", "description", "icon", "color")
        updates = [(field, values[field]) for field in fields if field in values]
        if not updates:
            return False
        assignments = [f"{field} = ?" for field, _ in updates]
        params: List[Any] = [value for _, value in updates]
        assignments.append("updated_at = ?")
        params.extend((datetime.now().isoformat(), category_id, user_id))
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                f"UPDATE task_categories SET {', '.join(assignments)} WHERE category_id = ? AND user_id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_category(self, user_id: str, category_id: str) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                """DELETE FROM task_categories
                   WHERE category_id = ? AND user_id = ? AND is_preset = 0""",
                (category_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def create_chain(
        self, user_id: str, chain_name: str, description: str, generation_status: str
    ) -> str:
        chain_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO task_chains
                   (chain_id, user_id, chain_name, description, generation_status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (chain_id, user_id, chain_name, description, generation_status, now, now),
            )
            conn.commit()
            return chain_id
        finally:
            conn.close()

    def list_chains(self, user_id: str) -> Sequence[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                """SELECT tc.*, COUNT(t.task_id) AS total_tasks,
                          COALESCE(SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_tasks
                   FROM task_chains tc LEFT JOIN tasks t ON t.chain_id = tc.chain_id
                   WHERE tc.user_id = ? GROUP BY tc.chain_id ORDER BY tc.created_at DESC""",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_chain(self, user_id: str, chain_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            row = conn.execute(
                "SELECT * FROM task_chains WHERE chain_id = ? AND user_id = ?", (chain_id, user_id)
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def delete_chain(self, user_id: str, chain_id: str) -> bool:
        conn = self._connection_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            exists = conn.execute(
                "SELECT 1 FROM task_chains WHERE chain_id = ? AND user_id = ?", (chain_id, user_id)
            ).fetchone()
            if exists is None:
                conn.rollback()
                return False
            delete_chain_projection(conn, user_id, chain_id)
            conn.execute("DELETE FROM tasks WHERE chain_id = ? AND user_id = ?", (chain_id, user_id))
            conn.execute("DELETE FROM task_chains WHERE chain_id = ? AND user_id = ?", (chain_id, user_id))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_chain_generation(
        self,
        user_id: str,
        chain_id: str,
        generation_status: str,
        generation_error: Optional[str] = None,
    ) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                """UPDATE task_chains
                   SET generation_status = ?, generation_error = ?, updated_at = ?
                   WHERE chain_id = ? AND user_id = ?""",
                (generation_status, generation_error, datetime.now().isoformat(), chain_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def create_chain_steps(
        self, user_id: str, chain_id: str, steps: Sequence[Mapping[str, Any]]
    ) -> List[str]:
        if not steps:
            return []
        conn = self._connection_factory()
        created: List[str] = []
        now = datetime.now().isoformat()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM task_chains WHERE chain_id = ? AND user_id = ?", (chain_id, user_id)
            ).fetchone() is None:
                raise ValueError("Task chain does not exist or is not owned by the user")
            for order, step in enumerate(steps, start=1):
                task_id = str(uuid.uuid4())
                prerequisites = [created[-1]] if created else []
                conn.execute(
                    """INSERT INTO tasks
                       (task_id, user_id, category_id, chain_id, chain_order, task_name, description,
                        related_attrs, estimated_time, reward_coins, priority, attribute_points,
                        prerequisites, completion_type, completion_criteria, task_type, is_optional,
                        is_daily, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        task_id, user_id, step.get("category_id"), chain_id, order,
                        str(step["title"]), str(step["description"]), json.dumps(step.get("related_attrs") or {}),
                        int(step["estimated_time"]), int(step["reward_coins"]), str(step["priority"]),
                        int(step["attribute_points"]), json.dumps(prerequisites), str(step["completion_type"]),
                        json.dumps(step.get("completion_criteria") or {}), str(step["task_type"]),
                        1 if step.get("is_optional") else 0, 1 if step.get("is_daily") else 0, now, now,
                    ),
                )
                created.append(task_id)
            conn.execute(
                """UPDATE task_chains
                   SET total_tasks = ?, status = 'active', generation_status = 'ready',
                       generation_error = NULL, updated_at = ?
                   WHERE chain_id = ? AND user_id = ?""",
                (len(created), now, chain_id, user_id),
            )
            chain = conn.execute(
                "SELECT * FROM task_chains WHERE chain_id = ? AND user_id = ?",
                (chain_id, user_id),
            ).fetchone()
            chain_tasks = conn.execute(
                """SELECT * FROM tasks WHERE chain_id = ? AND user_id = ?
                   ORDER BY chain_order, created_at""",
                (chain_id, user_id),
            ).fetchall()
            if chain is None or project_chain(
                conn, user_id, dict(chain), [dict(row) for row in chain_tasks], now
            ) is None:
                raise RuntimeError("Task chain execution projection was not created")
            conn.commit()
            return created
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
