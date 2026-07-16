"""SQLite Adapter for durable Task Execution."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from adapters.sqlite.task_repository import ConnectionFactory
from core.task_execution_contracts import TaskExecutionRepository


_JSON_FIELDS = {
    "metadata", "completion_criteria", "input_data", "output_data", "payload",
    "request_data", "decision_data", "checkpoint_data",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _observation_range(row: Optional[sqlite3.Row]) -> Dict[str, Optional[str]]:
    if row is None:
        return {"observed_from": None, "observed_to": None}
    return {"observed_from": row["observed_from"], "observed_to": row["observed_to"]}


def _decode(row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    value = dict(row)
    for field in _JSON_FIELDS:
        if field not in value:
            continue
        raw = value.get(field)
        try:
            value[field] = json.loads(raw) if raw else {}
        except (TypeError, json.JSONDecodeError):
            value[field] = {}
    for field in ("requires_approval",):
        if field in value:
            value[field] = bool(value[field])
    return value


def _insert_event(
    conn: sqlite3.Connection,
    user_id: str,
    run_id: str,
    event_type: str,
    *,
    step_id: Optional[str] = None,
    payload: Optional[Mapping[str, Any]] = None,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    event_id = str(uuid.uuid4())
    created_at = now or _now()
    conn.execute(
        """INSERT INTO task_events
           (event_id, run_id, step_id, user_id, event_type, payload, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (event_id, run_id, step_id, user_id, event_type, _json(payload), created_at),
    )
    return {
        "event_id": event_id,
        "run_id": run_id,
        "step_id": step_id,
        "user_id": user_id,
        "event_type": event_type,
        "payload": dict(payload or {}),
        "created_at": created_at,
    }


def _update_run_status(
    conn: sqlite3.Connection,
    user_id: str,
    run_id: str,
    expected: Sequence[str],
    target: str,
    *,
    error_summary: Optional[str] = None,
    now: Optional[str] = None,
) -> bool:
    if not expected:
        return False
    changed_at = now or _now()
    assignments = ["status = ?", "updated_at = ?", "version = version + 1"]
    params: list[Any] = [target, changed_at]
    timestamp_fields = {
        "running": "started_at",
        "paused": "paused_at",
        "completed": "completed_at",
        "cancelled": "cancelled_at",
    }
    if target in timestamp_fields:
        field = timestamp_fields[target]
        assignments.append(f"{field} = COALESCE({field}, ?)")
        params.append(changed_at)
    if target == "failed" or error_summary is not None:
        assignments.append("error_summary = ?")
        params.append(error_summary)
    placeholders = ", ".join("?" for _ in expected)
    params.extend((run_id, user_id, *expected))
    cursor = conn.execute(
        f"UPDATE task_runs SET {', '.join(assignments)} "
        f"WHERE run_id = ? AND user_id = ? AND status IN ({placeholders})",
        params,
    )
    return cursor.rowcount > 0


def _update_step_status(
    conn: sqlite3.Connection,
    user_id: str,
    run_id: str,
    step_id: str,
    expected: Sequence[str],
    target: str,
    *,
    output_data: Optional[Mapping[str, Any]] = None,
    error_summary: Optional[str] = None,
    increment_attempt: bool = False,
    now: Optional[str] = None,
) -> bool:
    if not expected:
        return False
    changed_at = now or _now()
    assignments = ["status = ?", "updated_at = ?"]
    params: list[Any] = [target, changed_at]
    if increment_attempt:
        assignments.append("attempt_count = attempt_count + 1")
    if target == "running":
        assignments.append("started_at = ?")
        params.append(changed_at)
    if target in ("completed", "skipped", "cancelled"):
        assignments.extend(["completed_at = ?", "progress = 100"])
        params.append(changed_at)
    if output_data is not None:
        assignments.append("output_data = ?")
        params.append(_json(output_data))
    if error_summary is not None:
        assignments.append("error_summary = ?")
        params.append(error_summary)
    placeholders = ", ".join("?" for _ in expected)
    params.extend((step_id, run_id, user_id, *expected))
    cursor = conn.execute(
        f"UPDATE task_steps SET {', '.join(assignments)} "
        f"WHERE step_id = ? AND run_id = ? AND user_id = ? AND status IN ({placeholders})",
        params,
    )
    return cursor.rowcount > 0


def _mark_ready_steps(
    conn: sqlite3.Connection, user_id: str, run_id: str, *, now: Optional[str] = None
) -> list[str]:
    changed_at = now or _now()
    rows = conn.execute(
        """SELECT s.step_id
           FROM task_steps s
           WHERE s.run_id = ? AND s.user_id = ? AND s.status = 'pending'
             AND NOT EXISTS (
                 SELECT 1 FROM task_step_dependencies d
                 JOIN task_steps parent ON parent.step_id = d.depends_on_step_id
                 WHERE d.run_id = s.run_id AND d.step_id = s.step_id
                   AND parent.status NOT IN ('completed', 'skipped')
             )
           ORDER BY s.position""",
        (run_id, user_id),
    ).fetchall()
    ready_ids: list[str] = []
    for row in rows:
        cursor = conn.execute(
            """UPDATE task_steps SET status = 'ready', updated_at = ?
               WHERE step_id = ? AND run_id = ? AND user_id = ? AND status = 'pending'""",
            (changed_at, row["step_id"], run_id, user_id),
        )
        if cursor.rowcount > 0:
            ready_ids.append(row["step_id"])
    return ready_ids


class SQLiteTaskExecutionRepository(TaskExecutionRepository):
    """Store execution state while keeping state policy in the Module."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def create_goal(self, user_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        goal_id = str(uuid.uuid4())
        now = _now()
        idempotency_key = values.get("idempotency_key")
        conn = self._connection_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if idempotency_key:
                existing = conn.execute(
                    "SELECT * FROM task_goals WHERE user_id = ? AND idempotency_key = ?",
                    (user_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    conn.rollback()
                    return _decode(existing) or {}
            conn.execute(
                """INSERT INTO task_goals
                   (goal_id, user_id, title, description, desired_outcome, status,
                    priority, idempotency_key, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)""",
                (
                    goal_id, user_id, values["title"], values.get("description", ""),
                    values.get("desired_outcome", ""), values.get("priority", "medium"),
                    idempotency_key, _json(values.get("metadata")), now, now,
                ),
            )
            conn.commit()
            return self.get_goal(user_id, goal_id) or {}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def list_goals(self, user_id: str, status: Optional[str] = None) -> Sequence[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM task_goals WHERE user_id = ? AND status = ? ORDER BY updated_at DESC",
                    (user_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM task_goals WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)
                ).fetchall()
            goals = []
            for row in rows:
                goal = _decode(row) or {}
                counts = conn.execute(
                    """SELECT COUNT(*) AS run_count,
                              COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed_runs
                       FROM task_runs WHERE goal_id = ? AND user_id = ?""",
                    (goal["goal_id"], user_id),
                ).fetchone()
                goal["run_count"] = counts["run_count"]
                goal["completed_runs"] = counts["completed_runs"]
                goals.append(goal)
            return goals
        finally:
            conn.close()

    def get_goal(self, user_id: str, goal_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(conn.execute(
                "SELECT * FROM task_goals WHERE goal_id = ? AND user_id = ?", (goal_id, user_id)
            ).fetchone())
        finally:
            conn.close()

    def update_goal(
        self, user_id: str, goal_id: str, values: Mapping[str, Any]
    ) -> bool:
        allowed = {"title", "description", "desired_outcome", "priority", "metadata", "status"}
        fields = [field for field in allowed if field in values]
        if not fields:
            return False
        assignments = [f"{field} = ?" for field in fields]
        params = [_json(values[field]) if field == "metadata" else values[field] for field in fields]
        conn = self._connection_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = _decode(conn.execute(
                "SELECT * FROM task_goals WHERE goal_id = ? AND user_id = ?", (goal_id, user_id)
            ).fetchone())
            if existing is None:
                conn.rollback()
                return False
            changed_fields = [field for field in fields if existing.get(field) != values[field]]
            now = _now()
            assignments.append("updated_at = ?")
            params.extend((now, goal_id, user_id))
            cursor = conn.execute(
                f"UPDATE task_goals SET {', '.join(assignments)} WHERE goal_id = ? AND user_id = ?",
                params,
            )
            if cursor.rowcount and changed_fields:
                planning_fields = {"title", "description", "desired_outcome", "priority"}
                change_kind = (
                    "plan_refined" if planning_fields.intersection(changed_fields)
                    else "status_changed" if "status" in changed_fields
                    else "metadata_changed"
                )
                conn.execute(
                    """INSERT INTO task_goal_changes
                       (change_id, goal_id, user_id, change_kind, changed_fields, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4()), goal_id, user_id, change_kind,
                        _json(sorted(changed_fields)), now,
                    ),
                )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_run(
        self,
        user_id: str,
        goal_id: str,
        values: Mapping[str, Any],
        steps: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        run_id = str(uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM task_goals WHERE goal_id = ? AND user_id = ?", (goal_id, user_id)
            ).fetchone() is None:
                raise ValueError("Goal does not exist")
            idempotency_key = values.get("idempotency_key")
            if idempotency_key:
                existing = conn.execute(
                    "SELECT run_id FROM task_runs WHERE user_id = ? AND idempotency_key = ?",
                    (user_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    conn.rollback()
                    return self.get_run(user_id, existing["run_id"]) or {}
            conn.execute(
                """INSERT INTO task_runs
                   (run_id, goal_id, user_id, title, objective, mode, status, idempotency_key,
                    metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?)""",
                (
                    run_id, goal_id, user_id, values["title"], values.get("objective", ""),
                    values.get("mode", "manual"), idempotency_key, _json(values.get("metadata")),
                    now, now,
                ),
            )
            key_to_id: Dict[str, str] = {}
            normalized_steps = []
            for position, step in enumerate(steps):
                step_id = str(uuid.uuid4())
                client_key = str(step.get("client_key") or f"step-{position + 1}")
                if client_key in key_to_id:
                    raise ValueError(f"Duplicate step key: {client_key}")
                key_to_id[client_key] = step_id
                normalized_steps.append((step_id, client_key, step, position))
                conn.execute(
                    """INSERT INTO task_steps
                       (step_id, run_id, user_id, client_key, title, description, kind, status,
                        position, parallel_group, attempt_count, max_attempts, requires_approval,
                        progress, completion_criteria, input_data, output_data, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, 0, ?, ?, 0, ?, ?, '{}', ?, ?)""",
                    (
                        step_id, run_id, user_id, client_key, step["title"], step.get("description", ""),
                        step.get("kind", "manual"), position, step.get("parallel_group"),
                        int(step.get("max_attempts", 1)), 1 if step.get("requires_approval") else 0,
                        _json(step.get("completion_criteria")), _json(step.get("input_data")), now, now,
                    ),
                )
            for step_id, _client_key, step, _position in normalized_steps:
                for dependency_key in step.get("depends_on", []):
                    dependency_id = key_to_id.get(str(dependency_key))
                    if dependency_id is None:
                        raise ValueError(f"Unknown step dependency: {dependency_key}")
                    if dependency_id == step_id:
                        raise ValueError("A step cannot depend on itself")
                    conn.execute(
                        """INSERT INTO task_step_dependencies
                           (run_id, step_id, depends_on_step_id) VALUES (?, ?, ?)""",
                        (run_id, step_id, dependency_id),
                    )
            conn.execute(
                """INSERT INTO task_events
                   (event_id, run_id, user_id, event_type, payload, created_at)
                   VALUES (?, ?, ?, 'run.created', ?, ?)""",
                (str(uuid.uuid4()), run_id, user_id, _json({"step_count": len(steps)}), now),
            )
            conn.commit()
            return self.get_run(user_id, run_id) or {}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def list_runs(
        self,
        user_id: str,
        *,
        goal_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Sequence[Dict[str, Any]]:
        clauses = ["r.user_id = ?"]
        params: list[Any] = [user_id]
        if goal_id:
            clauses.append("r.goal_id = ?")
            params.append(goal_id)
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                """SELECT r.*, g.title AS goal_title,
                          COUNT(s.step_id) AS step_count,
                          COALESCE(SUM(CASE WHEN s.status IN ('completed', 'skipped') THEN 1 ELSE 0 END), 0)
                              AS completed_steps
                   FROM task_runs r
                   JOIN task_goals g ON g.goal_id = r.goal_id
                   LEFT JOIN task_steps s ON s.run_id = r.run_id
                   WHERE """ + " AND ".join(clauses) +
                " GROUP BY r.run_id ORDER BY r.updated_at DESC",
                params,
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def summarize_profile_behavior(self, user_id: str) -> Dict[str, Any]:
        """Return aggregate execution signals without exposing review text or artifacts."""
        conn = self._connection_factory()
        try:
            totals = conn.execute(
                """SELECT
                       COUNT(*) AS run_count,
                       COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0)
                           AS completed_run_count,
                       COALESCE(SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 0)
                           AS cancelled_run_count,
                       COALESCE(SUM(CASE WHEN mode = 'agent' THEN 1 ELSE 0 END), 0)
                           AS agent_run_count,
                       MIN(created_at) AS observed_from,
                       MAX(COALESCE(completed_at, updated_at, created_at)) AS observed_to
                   FROM task_runs WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            steps = conn.execute(
                """SELECT
                       COUNT(*) AS step_count,
                       COALESCE(SUM(CASE WHEN status IN ('completed', 'skipped') THEN 1 ELSE 0 END), 0)
                           AS finished_step_count,
                       MIN(created_at) AS observed_from,
                       MAX(COALESCE(completed_at, updated_at, created_at)) AS observed_to
                   FROM task_steps WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            reviews = conn.execute(
                """SELECT
                       COUNT(*) AS review_count,
                       COALESCE(SUM(CASE WHEN next_action <> '' THEN 1 ELSE 0 END), 0)
                           AS review_with_next_action_count,
                       COALESCE(SUM(CASE WHEN notes <> '' THEN 1 ELSE 0 END), 0)
                           AS review_with_notes_count,
                       AVG(rating) AS average_rating,
                       MIN(created_at) AS observed_from,
                       MAX(updated_at) AS observed_to
                   FROM task_run_reviews WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            event_rows = conn.execute(
                """SELECT event_type, COUNT(*) AS event_count,
                          MIN(created_at) AS observed_from,
                          MAX(created_at) AS observed_to
                   FROM task_events
                   WHERE user_id = ? AND event_type IN ('run.paused', 'run.resumed', 'run.retry_requested')
                   GROUP BY event_type""",
                (user_id,),
            ).fetchall()
            events = {
                str(row["event_type"]): {
                    "count": int(row["event_count"]),
                    "observed_from": row["observed_from"],
                    "observed_to": row["observed_to"],
                }
                for row in event_rows
            }
            approvals = conn.execute(
                """SELECT
                       COUNT(CASE WHEN status IN ('approved', 'rejected') THEN 1 END) AS approval_count,
                       COALESCE(SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END), 0)
                           AS approved_approval_count,
                       COALESCE(SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END), 0)
                           AS rejected_approval_count,
                       MIN(CASE WHEN status IN ('approved', 'rejected') THEN resolved_at END) AS observed_from,
                       MAX(CASE WHEN status IN ('approved', 'rejected') THEN resolved_at END) AS observed_to
                   FROM task_approvals WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            goal_changes = conn.execute(
                """SELECT
                       COUNT(*) AS goal_change_count,
                       COALESCE(SUM(CASE WHEN change_kind = 'plan_refined' THEN 1 ELSE 0 END), 0)
                           AS goal_plan_refinement_count,
                       COUNT(DISTINCT CASE WHEN change_kind = 'plan_refined' THEN goal_id END)
                           AS refined_goal_count,
                       MIN(CASE WHEN change_kind = 'plan_refined' THEN created_at END) AS observed_from,
                       MAX(CASE WHEN change_kind = 'plan_refined' THEN created_at END) AS observed_to
                   FROM task_goal_changes WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
            return {
                "run_count": int(totals['run_count'] or 0),
                "completed_run_count": int(totals['completed_run_count'] or 0),
                "cancelled_run_count": int(totals['cancelled_run_count'] or 0),
                "agent_run_count": int(totals['agent_run_count'] or 0),
                "step_count": int(steps['step_count'] or 0),
                "finished_step_count": int(steps['finished_step_count'] or 0),
                "review_count": int(reviews['review_count'] or 0),
                "review_with_next_action_count": int(reviews['review_with_next_action_count'] or 0),
                "review_with_notes_count": int(reviews['review_with_notes_count'] or 0),
                "average_rating": float(reviews['average_rating']) if reviews['average_rating'] is not None else None,
                "pause_count": events.get('run.paused', {}).get("count", 0),
                "resume_count": events.get('run.resumed', {}).get("count", 0),
                "retry_count": events.get('run.retry_requested', {}).get("count", 0),
                "approval_count": int(approvals['approval_count'] or 0),
                "approved_approval_count": int(approvals['approved_approval_count'] or 0),
                "rejected_approval_count": int(approvals['rejected_approval_count'] or 0),
                "goal_change_count": int(goal_changes['goal_change_count'] or 0),
                "goal_plan_refinement_count": int(goal_changes['goal_plan_refinement_count'] or 0),
                "refined_goal_count": int(goal_changes['refined_goal_count'] or 0),
                "observation_ranges": {
                    "runs": _observation_range(totals),
                    "steps": _observation_range(steps),
                    "reviews": _observation_range(reviews),
                    "pauses": events.get("run.paused", _observation_range(None)),
                    "resumes": events.get("run.resumed", _observation_range(None)),
                    "approvals": _observation_range(approvals),
                    "goal_plan_refinements": _observation_range(goal_changes),
                },
            }
        finally:
            conn.close()

    def get_run(self, user_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            run = _decode(conn.execute(
                """SELECT r.*, g.title AS goal_title
                   FROM task_runs r JOIN task_goals g ON g.goal_id = r.goal_id
                   WHERE r.run_id = ? AND r.user_id = ?""",
                (run_id, user_id),
            ).fetchone())
            if run is None:
                return None
            step_rows = conn.execute(
                "SELECT * FROM task_steps WHERE run_id = ? AND user_id = ? ORDER BY position, created_at",
                (run_id, user_id),
            ).fetchall()
            steps = []
            for row in step_rows:
                step = _decode(row) or {}
                dependencies = conn.execute(
                    """SELECT parent.client_key, parent.step_id, parent.status
                       FROM task_step_dependencies d
                       JOIN task_steps parent ON parent.step_id = d.depends_on_step_id
                       WHERE d.run_id = ? AND d.step_id = ? ORDER BY parent.position""",
                    (run_id, step["step_id"]),
                ).fetchall()
                step["depends_on"] = [dict(item) for item in dependencies]
                steps.append(step)
            run["steps"] = steps
            run["artifacts"] = [
                _decode(row) or {} for row in conn.execute(
                    "SELECT * FROM task_artifacts WHERE run_id = ? AND user_id = ? ORDER BY created_at",
                    (run_id, user_id),
                ).fetchall()
            ]
            run["approvals"] = [
                _decode(row) or {} for row in conn.execute(
                    "SELECT * FROM task_approvals WHERE run_id = ? AND user_id = ? ORDER BY requested_at",
                    (run_id, user_id),
                ).fetchall()
            ]
            lease = _decode(conn.execute(
                """SELECT run_id, user_id, worker_id, acquired_at, heartbeat_at,
                          expires_at, checkpoint_data, released_at, version
                   FROM task_run_leases WHERE run_id = ? AND user_id = ?""",
                (run_id, user_id),
            ).fetchone())
            if lease is not None:
                lease["is_expired"] = bool(
                    lease.get("released_at") is None and lease.get("expires_at") <= _now()
                )
            run["lease"] = lease
            return run
        finally:
            conn.close()

    def compare_and_set_run_status(
        self,
        user_id: str,
        run_id: str,
        expected: Sequence[str],
        target: str,
        *,
        error_summary: Optional[str] = None,
    ) -> bool:
        conn = self._connection_factory()
        try:
            changed = _update_run_status(
                conn, user_id, run_id, expected, target, error_summary=error_summary
            )
            conn.commit()
            return changed
        finally:
            conn.close()

    def compare_and_set_step_status(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        expected: Sequence[str],
        target: str,
        *,
        output_data: Optional[Mapping[str, Any]] = None,
        error_summary: Optional[str] = None,
        increment_attempt: bool = False,
    ) -> bool:
        conn = self._connection_factory()
        try:
            changed = _update_step_status(
                conn,
                user_id,
                run_id,
                step_id,
                expected,
                target,
                output_data=output_data,
                error_summary=error_summary,
                increment_attempt=increment_attempt,
            )
            conn.commit()
            return changed
        finally:
            conn.close()

    def apply_run_transition(
        self,
        user_id: str,
        run_id: str,
        expected: Sequence[str],
        target: str,
        event_type: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
        error_summary: Optional[str] = None,
        cancel_open_steps: bool = False,
        publish_ready_steps: bool = False,
    ) -> bool:
        conn = self._connection_factory()
        now = _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if not _update_run_status(
                conn, user_id, run_id, expected, target, error_summary=error_summary, now=now
            ):
                conn.rollback()
                return False
            _insert_event(conn, user_id, run_id, event_type, payload=payload, now=now)
            if cancel_open_steps:
                rows = conn.execute(
                    """SELECT step_id FROM task_steps
                       WHERE run_id = ? AND user_id = ?
                         AND status NOT IN ('completed', 'failed', 'skipped', 'cancelled')""",
                    (run_id, user_id),
                ).fetchall()
                for row in rows:
                    if _update_step_status(
                        conn, user_id, run_id, row["step_id"],
                        ["pending", "ready", "running", "waiting_approval"],
                        "cancelled", now=now,
                    ):
                        _insert_event(
                            conn, user_id, run_id, "step.cancelled",
                            step_id=row["step_id"], payload=payload, now=now,
                        )
            if publish_ready_steps:
                for ready_step_id in _mark_ready_steps(conn, user_id, run_id, now=now):
                    _insert_event(
                        conn, user_id, run_id, "step.ready",
                        step_id=ready_step_id, now=now,
                    )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def apply_step_transition(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        expected: Sequence[str],
        target: str,
        event_type: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
        output_data: Optional[Mapping[str, Any]] = None,
        error_summary: Optional[str] = None,
        increment_attempt: bool = False,
        artifacts: Sequence[Mapping[str, Any]] = (),
        publish_ready_steps: bool = False,
        run_expected: Sequence[str] = (),
        run_target: Optional[str] = None,
        run_event_type: Optional[str] = None,
        run_payload: Optional[Mapping[str, Any]] = None,
        run_error_summary: Optional[str] = None,
        complete_run_if_satisfied: bool = False,
    ) -> Dict[str, Any]:
        conn = self._connection_factory()
        now = _now()
        artifact_ids: list[str] = []
        ready_step_ids: list[str] = []
        run_completed = False
        try:
            conn.execute("BEGIN IMMEDIATE")
            if not _update_step_status(
                conn, user_id, run_id, step_id, expected, target,
                output_data=output_data, error_summary=error_summary,
                increment_attempt=increment_attempt, now=now,
            ):
                conn.rollback()
                return {"changed": False}
            for artifact in artifacts:
                artifact_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO task_artifacts
                       (artifact_id, run_id, step_id, user_id, kind, title, uri,
                        content_type, metadata, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        artifact_id, run_id, step_id, user_id, artifact.get("kind", "result"),
                        artifact["title"], artifact.get("uri"), artifact.get("content_type"),
                        _json(artifact.get("metadata")), now,
                    ),
                )
                artifact_ids.append(artifact_id)
            event_payload = dict(payload or {})
            if artifact_ids:
                event_payload["artifact_ids"] = artifact_ids
            _insert_event(
                conn, user_id, run_id, event_type, step_id=step_id,
                payload=event_payload, now=now,
            )
            if publish_ready_steps:
                ready_step_ids = _mark_ready_steps(conn, user_id, run_id, now=now)
                for ready_step_id in ready_step_ids:
                    _insert_event(
                        conn, user_id, run_id, "step.ready",
                        step_id=ready_step_id, now=now,
                    )
            if run_target is not None:
                if not _update_run_status(
                    conn, user_id, run_id, run_expected, run_target,
                    error_summary=run_error_summary, now=now,
                ):
                    conn.rollback()
                    return {"changed": False, "run_conflict": True}
                _insert_event(
                    conn, user_id, run_id, run_event_type or f"run.{run_target}",
                    payload=run_payload, now=now,
                )
            if complete_run_if_satisfied:
                unfinished = conn.execute(
                    """SELECT 1 FROM task_steps
                       WHERE run_id = ? AND user_id = ?
                         AND status NOT IN ('completed', 'skipped') LIMIT 1""",
                    (run_id, user_id),
                ).fetchone()
                if unfinished is None and _update_run_status(
                    conn, user_id, run_id, ["running"], "completed", now=now
                ):
                    run_completed = True
                    _insert_event(conn, user_id, run_id, "run.completed", now=now)
            conn.commit()
            return {
                "changed": True,
                "artifact_ids": artifact_ids,
                "ready_step_ids": ready_step_ids,
                "run_completed": run_completed,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def mark_ready_steps(self, user_id: str, run_id: str) -> Sequence[str]:
        conn = self._connection_factory()
        now = _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                """SELECT s.step_id
                   FROM task_steps s
                   WHERE s.run_id = ? AND s.user_id = ? AND s.status = 'pending'
                     AND NOT EXISTS (
                         SELECT 1 FROM task_step_dependencies d
                         JOIN task_steps parent ON parent.step_id = d.depends_on_step_id
                         WHERE d.run_id = s.run_id AND d.step_id = s.step_id
                           AND parent.status NOT IN ('completed', 'skipped')
                     )
                   ORDER BY s.position""",
                (run_id, user_id),
            ).fetchall()
            step_ids = [row["step_id"] for row in rows]
            for step_id in step_ids:
                conn.execute(
                    "UPDATE task_steps SET status = 'ready', updated_at = ? WHERE step_id = ? AND status = 'pending'",
                    (now, step_id),
                )
            conn.commit()
            return step_ids
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def cancel_open_steps(self, user_id: str, run_id: str) -> None:
        conn = self._connection_factory()
        try:
            conn.execute(
                """UPDATE task_steps SET status = 'cancelled', completed_at = ?, updated_at = ?
                   WHERE run_id = ? AND user_id = ?
                     AND status NOT IN ('completed', 'failed', 'skipped', 'cancelled')""",
                (_now(), _now(), run_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def append_event(
        self,
        user_id: str,
        run_id: str,
        event_type: str,
        *,
        step_id: Optional[str] = None,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        event_id = str(uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO task_events
                   (event_id, run_id, step_id, user_id, event_type, payload, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_id, run_id, step_id, user_id, event_type, _json(payload), now),
            )
            conn.commit()
            return _decode(conn.execute(
                "SELECT * FROM task_events WHERE event_id = ?", (event_id,)
            ).fetchone()) or {}
        finally:
            conn.close()

    def list_events(self, user_id: str, run_id: str) -> Sequence[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return [_decode(row) or {} for row in conn.execute(
                "SELECT * FROM task_events WHERE run_id = ? AND user_id = ? ORDER BY created_at, event_id",
                (run_id, user_id),
            ).fetchall()]
        finally:
            conn.close()

    def get_run_review(self, user_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(conn.execute(
                "SELECT * FROM task_run_reviews WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone())
        finally:
            conn.close()

    def upsert_run_review(
        self,
        user_id: str,
        run_id: str,
        values: Mapping[str, Any],
    ) -> Dict[str, Any]:
        conn = self._connection_factory()
        now = _now()
        try:
            existing = conn.execute(
                "SELECT * FROM task_run_reviews WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """INSERT INTO task_run_reviews
                       (run_id, user_id, outcome, rating, notes, next_action, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        user_id,
                        values.get("outcome"),
                        values.get("rating"),
                        values.get("notes", ""),
                        values.get("next_action", ""),
                        now,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """UPDATE task_run_reviews
                       SET outcome = ?, rating = ?, notes = ?, next_action = ?, updated_at = ?
                       WHERE run_id = ? AND user_id = ?""",
                    (
                        values.get("outcome"),
                        values.get("rating"),
                        values.get("notes", ""),
                        values.get("next_action", ""),
                        now,
                        run_id,
                        user_id,
                    ),
                )
            conn.commit()
            return _decode(conn.execute(
                "SELECT * FROM task_run_reviews WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone()) or {}
        finally:
            conn.close()

    def list_run_reward_settlements(
        self, user_id: str, run_id: str
    ) -> Sequence[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return [_decode(row) or {} for row in conn.execute(
                """SELECT settlement_id, task_id, run_id, step_id, coins, experience,
                          attribute_increments, source, created_at
                   FROM task_reward_settlements
                   WHERE user_id = ? AND run_id = ?
                   ORDER BY created_at, settlement_id""",
                (user_id, run_id),
            ).fetchall()]
        finally:
            conn.close()

    def create_action(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        values: Mapping[str, Any],
    ) -> Dict[str, Any]:
        conn = self._connection_factory()
        try:
            idempotency_key = values.get("idempotency_key")
            if idempotency_key:
                existing = conn.execute(
                    """SELECT * FROM task_actions
                       WHERE step_id = ? AND user_id = ? AND idempotency_key = ?""",
                    (step_id, user_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    action = _decode(existing) or {}
                    action["_created"] = False
                    return action
            action_id = str(uuid.uuid4())
            now = _now()
            conn.execute(
                """INSERT INTO task_actions
                   (action_id, run_id, step_id, user_id, action_type, status, tool_name,
                    input_data, output_data, idempotency_key, started_at, created_at)
                   VALUES (?, ?, ?, ?, ?, 'running', ?, ?, '{}', ?, ?, ?)""",
                (
                    action_id, run_id, step_id, user_id, values.get("action_type", "manual"),
                    values.get("tool_name"), _json(values.get("input_data")), idempotency_key, now, now,
                ),
            )
            _insert_event(
                conn, user_id, run_id, "action.started", step_id=step_id,
                payload={"action_id": action_id, "action_type": values.get("action_type", "manual")},
                now=now,
            )
            conn.commit()
            action = _decode(conn.execute(
                "SELECT * FROM task_actions WHERE action_id = ?", (action_id,)
            ).fetchone()) or {}
            action["_created"] = True
            return action
        finally:
            conn.close()

    def complete_action(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        action_id: str,
        status: str,
        *,
        output_data: Optional[Mapping[str, Any]] = None,
        error_summary: Optional[str] = None,
    ) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                """UPDATE task_actions SET status = ?, output_data = ?, error_summary = ?, completed_at = ?
                   WHERE action_id = ? AND run_id = ? AND step_id = ? AND user_id = ?
                     AND status = 'running'""",
                (
                    status, _json(output_data), error_summary, _now(),
                    action_id, run_id, step_id, user_id,
                ),
            )
            if cursor.rowcount > 0:
                _insert_event(
                    conn, user_id, run_id, f"action.{status}", step_id=step_id,
                    payload={"action_id": action_id},
                )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def create_artifact(
        self,
        user_id: str,
        run_id: str,
        values: Mapping[str, Any],
        *,
        step_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        artifact_id = str(uuid.uuid4())
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO task_artifacts
                   (artifact_id, run_id, step_id, user_id, kind, title, uri, content_type, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    artifact_id, run_id, step_id, user_id, values.get("kind", "result"),
                    values["title"], values.get("uri"), values.get("content_type"),
                    _json(values.get("metadata")), _now(),
                ),
            )
            conn.commit()
            return _decode(conn.execute(
                "SELECT * FROM task_artifacts WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()) or {}
        finally:
            conn.close()

    def create_approval(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        request: Mapping[str, Any],
    ) -> Dict[str, Any]:
        conn = self._connection_factory()
        try:
            existing = conn.execute(
                """SELECT * FROM task_approvals
                   WHERE step_id = ? AND user_id = ? AND status = 'pending'""",
                (step_id, user_id),
            ).fetchone()
            if existing is not None:
                return _decode(existing) or {}
            approval_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO task_approvals
                   (approval_id, run_id, step_id, user_id, status, request_data, decision_data, requested_at)
                   VALUES (?, ?, ?, ?, 'pending', ?, '{}', ?)""",
                (approval_id, run_id, step_id, user_id, _json(request), _now()),
            )
            conn.commit()
            return _decode(conn.execute(
                "SELECT * FROM task_approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()) or {}
        finally:
            conn.close()

    def get_approval(self, user_id: str, approval_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(conn.execute(
                "SELECT * FROM task_approvals WHERE approval_id = ? AND user_id = ?",
                (approval_id, user_id),
            ).fetchone())
        finally:
            conn.close()

    def resolve_approval(
        self,
        user_id: str,
        approval_id: str,
        decision: str,
        note: Optional[str],
    ) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                """UPDATE task_approvals
                   SET status = ?, decision_data = ?, resolved_at = ?
                   WHERE approval_id = ? AND user_id = ? AND status = 'pending'""",
                (decision, _json({"decision": decision, "note": note}), _now(), approval_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def request_approval_transition(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        expected_step_status: str,
        request: Mapping[str, Any],
    ) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        now = _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                """SELECT * FROM task_approvals
                   WHERE run_id = ? AND step_id = ? AND user_id = ? AND status = 'pending'""",
                (run_id, step_id, user_id),
            ).fetchone()
            if existing is not None:
                conn.rollback()
                return _decode(existing)
            approval_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO task_approvals
                   (approval_id, run_id, step_id, user_id, status, request_data,
                    decision_data, requested_at)
                   VALUES (?, ?, ?, ?, 'pending', ?, '{}', ?)""",
                (approval_id, run_id, step_id, user_id, _json(request), now),
            )
            if not _update_step_status(
                conn, user_id, run_id, step_id, [expected_step_status],
                "waiting_approval", now=now,
            ) or not _update_run_status(
                conn, user_id, run_id, ["running"], "waiting_approval", now=now
            ):
                conn.rollback()
                return None
            payload = {"approval_id": approval_id, "step_id": step_id}
            _insert_event(
                conn, user_id, run_id, "run.waiting_approval", payload=payload, now=now
            )
            _insert_event(
                conn, user_id, run_id, "approval.requested", step_id=step_id,
                payload={"approval_id": approval_id}, now=now,
            )
            conn.commit()
            return _decode(conn.execute(
                "SELECT * FROM task_approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone())
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def resolve_approval_transition(
        self,
        user_id: str,
        approval_id: str,
        decision: str,
        note: Optional[str],
    ) -> Optional[str]:
        conn = self._connection_factory()
        now = _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            approval = conn.execute(
                """SELECT * FROM task_approvals
                   WHERE approval_id = ? AND user_id = ? AND status = 'pending'""",
                (approval_id, user_id),
            ).fetchone()
            if approval is None:
                conn.rollback()
                return None
            run_id = approval["run_id"]
            step_id = approval["step_id"]
            target = "ready" if decision == "approved" else "failed"
            run_target = "running" if decision == "approved" else "failed"
            error = None if decision == "approved" else (note or "Approval rejected")
            cursor = conn.execute(
                """UPDATE task_approvals
                   SET status = ?, decision_data = ?, resolved_at = ?
                   WHERE approval_id = ? AND user_id = ? AND status = 'pending'""",
                (decision, _json({"decision": decision, "note": note}), now, approval_id, user_id),
            )
            if cursor.rowcount == 0 or not _update_step_status(
                conn, user_id, run_id, step_id, ["waiting_approval"], target,
                error_summary=error, now=now,
            ) or not _update_run_status(
                conn, user_id, run_id, ["waiting_approval"], run_target,
                error_summary=error, now=now,
            ):
                conn.rollback()
                return None
            _insert_event(
                conn, user_id, run_id, f"approval.{decision}", step_id=step_id,
                payload={"approval_id": approval_id, "note": note}, now=now,
            )
            conn.commit()
            return str(run_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def claim_run_lease(
        self,
        user_id: str,
        run_id: str,
        worker_id: str,
        lease_seconds: int,
    ) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        expires_at = (now_dt + timedelta(seconds=lease_seconds)).isoformat()
        try:
            conn.execute("BEGIN IMMEDIATE")
            run = conn.execute(
                "SELECT mode, status FROM task_runs WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone()
            if run is None or run["mode"] != "agent" or run["status"] != "running":
                conn.rollback()
                return None
            existing = conn.execute(
                "SELECT * FROM task_run_leases WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone()
            reclaimed = False
            previous_worker_id = None
            if existing is not None:
                is_active = existing["released_at"] is None and existing["expires_at"] > now
                if is_active and existing["worker_id"] != worker_id:
                    conn.rollback()
                    return None
                if is_active:
                    conn.execute(
                        """UPDATE task_run_leases
                           SET heartbeat_at = ?, expires_at = ?, version = version + 1
                           WHERE run_id = ? AND user_id = ?""",
                        (now, expires_at, run_id, user_id),
                    )
                else:
                    reclaimed = existing["released_at"] is None
                    previous_worker_id = existing["worker_id"]
                    lease_token = str(uuid.uuid4())
                    conn.execute(
                        """UPDATE task_run_leases
                           SET worker_id = ?, lease_token = ?, acquired_at = ?, heartbeat_at = ?,
                               expires_at = ?, released_at = NULL, version = version + 1
                           WHERE run_id = ? AND user_id = ?""",
                        (worker_id, lease_token, now, now, expires_at, run_id, user_id),
                    )
            else:
                lease_token = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO task_run_leases
                       (run_id, user_id, worker_id, lease_token, acquired_at, heartbeat_at,
                        expires_at, checkpoint_data, released_at, version)
                       VALUES (?, ?, ?, ?, ?, ?, ?, '{}', NULL, 1)""",
                    (run_id, user_id, worker_id, lease_token, now, now, expires_at),
                )
            event_type = "run.lease_reclaimed" if reclaimed else "run.lease_claimed"
            _insert_event(
                conn, user_id, run_id, event_type,
                payload={
                    "worker_id": worker_id,
                    "previous_worker_id": previous_worker_id,
                    "expires_at": expires_at,
                },
                now=now,
            )
            conn.commit()
            return _decode(conn.execute(
                "SELECT * FROM task_run_leases WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone())
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def heartbeat_run_lease(
        self,
        user_id: str,
        run_id: str,
        lease_token: str,
        lease_seconds: int,
        checkpoint_data: Optional[Mapping[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        expires_at = (now_dt + timedelta(seconds=lease_seconds)).isoformat()
        try:
            conn.execute("BEGIN IMMEDIATE")
            assignments = ["heartbeat_at = ?", "expires_at = ?", "version = version + 1"]
            params: list[Any] = [now, expires_at]
            if checkpoint_data is not None:
                assignments.append("checkpoint_data = ?")
                params.append(_json(checkpoint_data))
            params.extend((run_id, user_id, lease_token, now))
            cursor = conn.execute(
                f"""UPDATE task_run_leases SET {', '.join(assignments)}
                    WHERE run_id = ? AND user_id = ? AND lease_token = ?
                      AND released_at IS NULL AND expires_at > ?""",
                params,
            )
            if cursor.rowcount == 0:
                conn.rollback()
                return None
            if checkpoint_data is not None:
                _insert_event(
                    conn, user_id, run_id, "run.checkpointed",
                    payload={"checkpoint": dict(checkpoint_data)}, now=now,
                )
            conn.commit()
            return _decode(conn.execute(
                "SELECT * FROM task_run_leases WHERE run_id = ? AND user_id = ?",
                (run_id, user_id),
            ).fetchone())
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def release_run_lease(
        self,
        user_id: str,
        run_id: str,
        lease_token: str,
        *,
        checkpoint_data: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        conn = self._connection_factory()
        now = _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            assignments = ["released_at = ?", "heartbeat_at = ?", "version = version + 1"]
            params: list[Any] = [now, now]
            if checkpoint_data is not None:
                assignments.append("checkpoint_data = ?")
                params.append(_json(checkpoint_data))
            params.extend((run_id, user_id, lease_token))
            cursor = conn.execute(
                f"""UPDATE task_run_leases SET {', '.join(assignments)}
                    WHERE run_id = ? AND user_id = ? AND lease_token = ?
                      AND released_at IS NULL""",
                params,
            )
            if cursor.rowcount == 0:
                conn.rollback()
                return False
            _insert_event(
                conn, user_id, run_id, "run.lease_released",
                payload={"checkpoint_saved": checkpoint_data is not None}, now=now,
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
