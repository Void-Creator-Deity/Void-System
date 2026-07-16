"""SQLite adapter for the task workspace and task catalog module."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence

from adapters.sqlite.task_execution_projection import (
    append_chain_task_execution,
    create_chain_task_execution,
    create_standalone_task_execution,
    delete_chain_projection,
    delete_task_projection,
    link_legacy_chain_execution,
    link_legacy_task_execution,
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
        chain_id = values.get("chain_id")
        if chain_id:
            # Route all workflow membership through the canonical chain builder.
            return self.create_chain_steps(
                user_id,
                str(chain_id),
                [{**values, "title": str(values["task_name"])}],
            )[0]

        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = self._connection_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            execution = create_standalone_task_execution(
                conn,
                user_id,
                {**values, "task_id": task_id},
                now,
            )
            conn.execute(
                """INSERT INTO tasks
                   (task_id, user_id, category_id, chain_id, chain_order, task_name, description,
                    related_attrs, estimated_time, reward_coins, priority, attribute_points,
                    prerequisites, completion_type, completion_criteria, task_type, is_optional,
                    is_daily, created_at, updated_at)
                   VALUES (?, ?, ?, NULL, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    user_id,
                    values.get("category_id"),
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
            link_legacy_task_execution(conn, user_id, task_id, None, execution, now)
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

    def get_execution_link(
        self, user_id: str, task_id: str
    ) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            row = conn.execute(
                """SELECT goal_id, run_id, step_id FROM legacy_task_execution_links
                   WHERE legacy_task_id = ? AND user_id = ?""",
                (task_id, user_id),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def legacy_execution_audit(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        clauses = []
        params: List[Any] = []
        if user_id is not None:
            clauses.append("l.user_id = ?")
            params.append(user_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        conn = self._connection_factory()
        try:
            task_rows = conn.execute(
                """SELECT l.user_id, l.legacy_task_id, l.legacy_chain_id, l.goal_id, l.run_id,
                          l.step_id, t.status AS legacy_status, s.status AS step_status
                   FROM legacy_task_execution_links l
                   LEFT JOIN tasks t ON t.task_id = l.legacy_task_id AND t.user_id = l.user_id
                   LEFT JOIN task_steps s ON s.step_id = l.step_id AND s.user_id = l.user_id"""
                + where
                + " ORDER BY l.user_id, l.legacy_chain_id, l.legacy_task_id",
                params,
            ).fetchall()
            chain_rows = conn.execute(
                """SELECT l.user_id, l.legacy_chain_id, l.goal_id, l.run_id, c.status AS legacy_status
                   FROM legacy_chain_execution_links l
                   LEFT JOIN task_chains c ON c.chain_id = l.legacy_chain_id AND c.user_id = l.user_id"""
                + where
                + " ORDER BY l.user_id, l.legacy_chain_id",
                params,
            ).fetchall()
            tasks = [dict(row) for row in task_rows]
            chains = [dict(row) for row in chain_rows]
            owners = sorted({str(row["user_id"]) for row in tasks + chains})
            status_counts: Dict[str, int] = {}
            for row in tasks:
                status = str(row.get("legacy_status") or "missing")
                status_counts[status] = status_counts.get(status, 0) + 1
            return {
                "summary": {
                    "owner_count": len(owners),
                    "task_link_count": len(tasks),
                    "chain_link_count": len(chains),
                    "task_status_counts": status_counts,
                },
                "tasks": tasks,
                "chains": chains,
            }
        finally:
            conn.close()

    def get_chain_execution_link(
        self, user_id: str, chain_id: str
    ) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            row = conn.execute(
                """SELECT goal_id, run_id FROM legacy_chain_execution_links
                   WHERE legacy_chain_id = ? AND user_id = ?""",
                (chain_id, user_id),
            ).fetchone()
            return dict(row) if row is not None else None
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
            task = conn.execute(
                "SELECT 1 FROM tasks WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            ).fetchone()
            if task is None:
                conn.rollback()
                return False
            if not sync_task_progress(conn, user_id, task_id, normalized, now):
                raise RuntimeError("Task is missing its canonical execution Step")
            conn.execute(
                """UPDATE tasks SET current_progress = ?, updated_at = ?
                   WHERE task_id = ? AND user_id = ?""",
                (normalized, now, task_id, user_id),
            )
            conn.commit()
            return True
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
            chain = conn.execute(
                "SELECT * FROM task_chains WHERE chain_id = ? AND user_id = ?",
                (chain_id, user_id),
            ).fetchone()
            if chain is None:
                raise ValueError("Task chain does not exist or is not owned by the user")

            existing_tasks = conn.execute(
                """SELECT task_id, chain_order, created_at FROM tasks
                   WHERE chain_id = ? AND user_id = ? ORDER BY chain_order, created_at""",
                (chain_id, user_id),
            ).fetchall()
            next_order = max((int(row["chain_order"] or 0) for row in existing_tasks), default=0) + 1
            previous_task_id = str(existing_tasks[-1]["task_id"]) if existing_tasks else None
            planned_steps: List[Dict[str, Any]] = []
            for offset, step in enumerate(steps):
                task_id = str(uuid.uuid4())
                raw_prerequisites = step.get("prerequisites")
                prerequisites = (
                    [str(item) for item in raw_prerequisites]
                    if isinstance(raw_prerequisites, list)
                    else ([previous_task_id] if previous_task_id else [])
                )
                planned_steps.append(
                    {
                        **step,
                        "task_id": task_id,
                        "task_name": str(step["title"]),
                        "chain_id": chain_id,
                        "chain_order": next_order + offset,
                        "prerequisites": prerequisites,
                        "created_at": now,
                    }
                )
                created.append(task_id)
                previous_task_id = task_id

            existing_link = conn.execute(
                """SELECT goal_id, run_id FROM legacy_chain_execution_links
                   WHERE legacy_chain_id = ? AND user_id = ?""",
                (chain_id, user_id),
            ).fetchone()
            if existing_link is None and existing_tasks:
                # This bridge is only for task chains that predate canonical execution.
                legacy_rows = conn.execute(
                    """SELECT * FROM tasks WHERE chain_id = ? AND user_id = ?
                       ORDER BY chain_order, created_at""",
                    (chain_id, user_id),
                ).fetchall()
                if project_chain(
                    conn, user_id, dict(chain), [dict(row) for row in legacy_rows], now
                ) is None:
                    raise RuntimeError("Historical task chain migration was not created")
                existing_link = conn.execute(
                    """SELECT goal_id, run_id FROM legacy_chain_execution_links
                       WHERE legacy_chain_id = ? AND user_id = ?""",
                    (chain_id, user_id),
                ).fetchone()

            created_chain_execution = existing_link is None
            if created_chain_execution:
                execution = create_chain_task_execution(
                    conn, user_id, dict(chain), planned_steps, now
                )
            else:
                execution = append_chain_task_execution(
                    conn, user_id, chain_id, planned_steps, now
                )
            if execution is None:
                raise RuntimeError("Task chain canonical execution was not created")

            for step in planned_steps:
                conn.execute(
                    """INSERT INTO tasks
                       (task_id, user_id, category_id, chain_id, chain_order, task_name, description,
                        related_attrs, estimated_time, reward_coins, priority, attribute_points,
                        prerequisites, completion_type, completion_criteria, task_type, is_optional,
                        is_daily, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        step["task_id"], user_id, step.get("category_id"), chain_id,
                        int(step["chain_order"]), str(step["task_name"]), str(step["description"]),
                        json.dumps(step.get("related_attrs") or {}), int(step["estimated_time"]),
                        int(step["reward_coins"]), str(step["priority"]), int(step["attribute_points"]),
                        json.dumps(step["prerequisites"]), str(step["completion_type"]),
                        json.dumps(step.get("completion_criteria") or {}), str(step["task_type"]),
                        1 if step.get("is_optional") else 0, 1 if step.get("is_daily") else 0, now, now,
                    ),
                )

            conn.execute(
                """UPDATE task_chains
                   SET total_tasks = ?, status = 'active', generation_status = 'ready',
                       generation_error = NULL, updated_at = ?
                   WHERE chain_id = ? AND user_id = ?""",
                (len(existing_tasks) + len(created), now, chain_id, user_id),
            )
            if created_chain_execution:
                link_legacy_chain_execution(conn, user_id, chain_id, execution, now)
            for task_id in created:
                link_legacy_task_execution(
                    conn,
                    user_id,
                    task_id,
                    chain_id,
                    {
                        "goal_id": str(execution["goal_id"]),
                        "run_id": str(execution["run_id"]),
                        "step_id": str(execution["steps"][task_id]),
                    },
                    now,
                )
            conn.commit()
            return created
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
