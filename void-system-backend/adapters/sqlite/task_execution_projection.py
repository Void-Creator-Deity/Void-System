"""Compatibility projection from legacy tasks into canonical task execution records."""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Dict, Mapping, Optional, Sequence


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _load_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        parsed = json.loads(value) if value else []
    except (TypeError, json.JSONDecodeError):
        parsed = []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _event(
    conn: sqlite3.Connection,
    user_id: str,
    run_id: str,
    event_type: str,
    now: str,
    *,
    step_id: Optional[str] = None,
    payload: Optional[Mapping[str, Any]] = None,
) -> None:
    conn.execute(
        """INSERT INTO task_events
           (event_id, run_id, step_id, user_id, event_type, payload, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), run_id, step_id, user_id, event_type, _json(payload), now),
    )


def _legacy_step_status(status: str) -> str:
    return {
        "in_progress": "running",
        "completed": "completed",
        "failed": "failed",
        "pending_evaluation": "waiting_approval",
    }.get(status, "pending")


def _run_status(step_statuses: Sequence[str]) -> str:
    if step_statuses and all(status in {"completed", "skipped"} for status in step_statuses):
        return "completed"
    if any(status == "failed" for status in step_statuses):
        return "failed"
    if any(status == "waiting_approval" for status in step_statuses):
        return "waiting_approval"
    if any(status in {"running", "completed", "skipped"} for status in step_statuses):
        return "running"
    return "queued"


def _timestamps(status: str, now: str) -> tuple[Optional[str], Optional[str]]:
    started_at = now if status in {"running", "waiting_approval", "completed", "failed"} else None
    completed_at = now if status == "completed" else None
    return started_at, completed_at


def _insert_goal(
    conn: sqlite3.Connection,
    user_id: str,
    title: str,
    description: str,
    priority: str,
    metadata: Mapping[str, Any],
    now: str,
    *,
    completed: bool = False,
) -> str:
    goal_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO task_goals
           (goal_id, user_id, title, description, desired_outcome, status, priority,
            metadata, created_at, updated_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            goal_id,
            user_id,
            title,
            description,
            description,
            "completed" if completed else "active",
            priority,
            _json(metadata),
            now,
            now,
            now if completed else None,
        ),
    )
    return goal_id


def _ensure_pending_approval(
    conn: sqlite3.Connection,
    user_id: str,
    run_id: str,
    step_id: str,
    task_id: str,
    now: str,
) -> None:
    pending = conn.execute(
        """SELECT 1 FROM task_approvals
           WHERE run_id = ? AND step_id = ? AND user_id = ? AND status = 'pending'""",
        (run_id, step_id, user_id),
    ).fetchone()
    if pending is not None:
        return
    conn.execute(
        """INSERT INTO task_approvals
           (approval_id, run_id, step_id, user_id, status, request_data,
            decision_data, requested_at, resolved_at)
           VALUES (?, ?, ?, ?, 'pending', ?, '{}', ?, NULL)""",
        (
            str(uuid.uuid4()),
            run_id,
            step_id,
            user_id,
            _json({"source": "legacy_proof", "legacy_task_id": task_id}),
            now,
        ),
    )
    _event(
        conn,
        user_id,
        run_id,
        "approval.requested",
        now,
        step_id=step_id,
        payload={"source": "legacy_proof", "legacy_task_id": task_id},
    )


def _resolve_pending_approvals(
    conn: sqlite3.Connection,
    user_id: str,
    run_id: str,
    step_id: str,
    task_id: str,
    decision: str,
    now: str,
) -> None:
    approvals = conn.execute(
        """SELECT approval_id FROM task_approvals
           WHERE run_id = ? AND step_id = ? AND user_id = ? AND status = 'pending'""",
        (run_id, step_id, user_id),
    ).fetchall()
    for approval in approvals:
        conn.execute(
            """UPDATE task_approvals
               SET status = ?, decision_data = ?, resolved_at = ?
               WHERE approval_id = ? AND status = 'pending'""",
            (
                decision,
                _json({"source": "legacy_task_status", "legacy_task_id": task_id}),
                now,
                approval["approval_id"],
            ),
        )
        _event(
            conn,
            user_id,
            run_id,
            "approval.resolved",
            now,
            step_id=step_id,
            payload={"decision": decision, "legacy_task_id": task_id},
        )


def _refresh_dependency_readiness(
    conn: sqlite3.Connection, user_id: str, run_id: str, now: str, *, emit_events: bool
) -> None:
    blocked_ready = conn.execute(
        """SELECT s.step_id FROM task_steps s
           WHERE s.run_id = ? AND s.user_id = ? AND s.status = 'ready'
             AND EXISTS (
                 SELECT 1 FROM task_step_dependencies d
                 JOIN task_steps parent ON parent.step_id = d.depends_on_step_id
                 WHERE d.step_id = s.step_id AND parent.status NOT IN ('completed', 'skipped')
             )""",
        (run_id, user_id),
    ).fetchall()
    for row in blocked_ready:
        conn.execute(
            "UPDATE task_steps SET status = 'pending', updated_at = ? WHERE step_id = ?",
            (now, row["step_id"]),
        )

    newly_ready = conn.execute(
        """SELECT s.step_id FROM task_steps s
           WHERE s.run_id = ? AND s.user_id = ? AND s.status = 'pending'
             AND NOT EXISTS (
                 SELECT 1 FROM task_step_dependencies d
                 JOIN task_steps parent ON parent.step_id = d.depends_on_step_id
                 WHERE d.step_id = s.step_id AND parent.status NOT IN ('completed', 'skipped')
             )""",
        (run_id, user_id),
    ).fetchall()
    for row in newly_ready:
        conn.execute(
            "UPDATE task_steps SET status = 'ready', updated_at = ? WHERE step_id = ?",
            (now, row["step_id"]),
        )
        if emit_events:
            _event(conn, user_id, run_id, "step.ready", now, step_id=row["step_id"])


def _sync_run_and_goal(
    conn: sqlite3.Connection, user_id: str, goal_id: str, run_id: str, now: str, *, reason: str
) -> str:
    run = conn.execute(
        "SELECT status FROM task_runs WHERE run_id = ? AND user_id = ?", (run_id, user_id)
    ).fetchone()
    statuses = [
        row["status"]
        for row in conn.execute(
            "SELECT status FROM task_steps WHERE run_id = ? AND user_id = ? ORDER BY position",
            (run_id, user_id),
        ).fetchall()
    ]
    target = _run_status(statuses)
    if run is not None and run["status"] != target:
        assignments = ["status = ?", "updated_at = ?", "version = version + 1"]
        params: list[Any] = [target, now]
        if target in {"running", "waiting_approval", "completed", "failed"}:
            assignments.append("started_at = COALESCE(started_at, ?)")
            params.append(now)
        if target == "completed":
            assignments.append("completed_at = COALESCE(completed_at, ?)")
            params.append(now)
        else:
            assignments.append("completed_at = NULL")
        params.extend((run_id, user_id))
        conn.execute(
            f"UPDATE task_runs SET {', '.join(assignments)} WHERE run_id = ? AND user_id = ?",
            params,
        )
        _event(conn, user_id, run_id, f"legacy.run.{target}", now, payload={"reason": reason})
    if target == "completed":
        conn.execute(
            """UPDATE task_goals SET status = 'completed', completed_at = COALESCE(completed_at, ?),
                      updated_at = ? WHERE goal_id = ? AND user_id = ?""",
            (now, now, goal_id, user_id),
        )
    else:
        conn.execute(
            """UPDATE task_goals SET status = 'active', completed_at = NULL, updated_at = ?
               WHERE goal_id = ? AND user_id = ?""",
            (now, goal_id, user_id),
        )
    return target


def _insert_step(
    conn: sqlite3.Connection,
    user_id: str,
    goal_id: str,
    run_id: str,
    task: Mapping[str, Any],
    now: str,
    *,
    position: int,
    chain_id: Optional[str],
    link_legacy_task: bool = True,
) -> str:
    task_id = str(task["task_id"])
    status = _legacy_step_status(str(task.get("status") or "pending"))
    started_at, completed_at = _timestamps(status, now)
    step_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO task_steps
           (step_id, run_id, user_id, client_key, title, description, kind, status,
            position, attempt_count, max_attempts, requires_approval, progress,
            completion_criteria, input_data, output_data, error_summary, created_at,
            updated_at, started_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, 'manual', ?, ?, ?, 3, ?, ?, ?, ?, '{}', ?, ?, ?, ?, ?)""",
        (
            step_id,
            run_id,
            user_id,
            task_id,
            str(task.get("task_name") or "Task"),
            str(task.get("description") or ""),
            status,
            position,
            1 if status in {"running", "waiting_approval", "completed", "failed"} else 0,
            1 if status == "waiting_approval" else 0,
            100 if status == "completed" else int(task.get("current_progress") or 0),
            _json(task.get("completion_criteria")),
            _json({"legacy_task_id": task_id}),
            "Legacy task failed" if status == "failed" else None,
            now,
            now,
            started_at,
            completed_at,
        ),
    )
    if link_legacy_task:
        _link_legacy_task_execution(
            conn,
            user_id,
            task_id,
            chain_id,
            goal_id,
            run_id,
            step_id,
            now,
        )
    if status == "waiting_approval":
        _ensure_pending_approval(conn, user_id, run_id, step_id, task_id, now)
    return step_id


def _link_legacy_task_execution(
    conn: sqlite3.Connection,
    user_id: str,
    task_id: str,
    chain_id: Optional[str],
    goal_id: str,
    run_id: str,
    step_id: str,
    now: str,
) -> None:
    conn.execute(
        """INSERT INTO legacy_task_execution_links
           (legacy_task_id, user_id, legacy_chain_id, goal_id, run_id, step_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (task_id, user_id, chain_id, goal_id, run_id, step_id, now),
    )


def link_legacy_task_execution(
    conn: sqlite3.Connection,
    user_id: str,
    task_id: str,
    chain_id: Optional[str],
    execution: Mapping[str, str],
    now: str,
) -> None:
    """Attach a legacy read record after its canonical execution is durable."""
    _link_legacy_task_execution(
        conn,
        user_id,
        task_id,
        chain_id,
        str(execution["goal_id"]),
        str(execution["run_id"]),
        str(execution["step_id"]),
        now,
    )


def link_legacy_chain_execution(
    conn: sqlite3.Connection,
    user_id: str,
    chain_id: str,
    execution: Mapping[str, str],
    now: str,
) -> None:
    """Attach a legacy workflow record after the Goal and Run have been created."""
    conn.execute(
        """INSERT INTO legacy_chain_execution_links
           (legacy_chain_id, user_id, goal_id, run_id, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (chain_id, user_id, str(execution["goal_id"]), str(execution["run_id"]), now),
    )


def create_standalone_task_execution(
    conn: sqlite3.Connection,
    user_id: str,
    task: Mapping[str, Any],
    now: str,
) -> Dict[str, str]:
    """Create canonical records before materializing a legacy task read record."""
    task_id = str(task["task_id"])
    legacy_status = _legacy_step_status(str(task.get("status") or "pending"))
    title = str(task.get("task_name") or "Legacy task")
    description = str(task.get("description") or "")
    goal_id = _insert_goal(
        conn,
        user_id,
        title,
        description,
        str(task.get("priority") or "medium"),
        {"legacy_task_id": task_id},
        now,
        completed=legacy_status == "completed",
    )
    run_id = str(uuid.uuid4())
    run_status = _run_status([legacy_status])
    started_at, completed_at = _timestamps(run_status, now)
    conn.execute(
        """INSERT INTO task_runs
           (run_id, goal_id, user_id, title, objective, mode, status, version,
            idempotency_key, metadata, created_at, updated_at, started_at, completed_at, error_summary)
           VALUES (?, ?, ?, ?, ?, 'manual', ?, 1, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            goal_id,
            user_id,
            title,
            description,
            run_status,
            f"legacy-task:{task_id}",
            _json({"legacy_task_id": task_id}),
            now,
            now,
            started_at,
            completed_at,
            "Legacy task failed" if run_status == "failed" else None,
        ),
    )
    step_id = _insert_step(
        conn,
        user_id,
        goal_id,
        run_id,
        task,
        now,
        position=0,
        chain_id=None,
        link_legacy_task=False,
    )
    _refresh_dependency_readiness(conn, user_id, run_id, now, emit_events=False)
    _event(
        conn,
        user_id,
        run_id,
        "legacy.task_canonical_created",
        now,
        step_id=step_id,
        payload={"legacy_task_id": task_id},
    )
    return {"goal_id": goal_id, "run_id": run_id, "step_id": step_id}


def create_chain_task_execution(
    conn: sqlite3.Connection,
    user_id: str,
    chain: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
    now: str,
) -> Optional[Dict[str, Any]]:
    """Create a canonical dependency graph before its legacy task-chain read records."""
    if not tasks:
        return None
    chain_id = str(chain["chain_id"])
    ordered = sorted(
        tasks,
        key=lambda item: (int(item.get("chain_order") or 0), str(item.get("created_at") or "")),
    )
    statuses = [_legacy_step_status(str(task.get("status") or "pending")) for task in ordered]
    run_status = _run_status(statuses)
    title = str(chain.get("chain_name") or "Legacy workflow")
    description = str(chain.get("description") or "")
    goal_id = _insert_goal(
        conn,
        user_id,
        title,
        description,
        str(ordered[0].get("priority") or "medium"),
        {"legacy_chain_id": chain_id},
        now,
        completed=run_status == "completed",
    )
    run_id = str(uuid.uuid4())
    started_at, completed_at = _timestamps(run_status, now)
    conn.execute(
        """INSERT INTO task_runs
           (run_id, goal_id, user_id, title, objective, mode, status, version,
            idempotency_key, metadata, created_at, updated_at, started_at, completed_at, error_summary)
           VALUES (?, ?, ?, ?, ?, 'manual', ?, 1, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            goal_id,
            user_id,
            title,
            description,
            run_status,
            f"legacy-chain:{chain_id}",
            _json({"legacy_chain_id": chain_id}),
            now,
            now,
            started_at,
            completed_at,
            "Legacy workflow failed" if run_status == "failed" else None,
        ),
    )
    task_to_step: Dict[str, str] = {}
    for position, task in enumerate(ordered):
        task_id = str(task["task_id"])
        task_to_step[task_id] = _insert_step(
            conn,
            user_id,
            goal_id,
            run_id,
            task,
            now,
            position=position,
            chain_id=chain_id,
            link_legacy_task=False,
        )
    for position, task in enumerate(ordered):
        task_id = str(task["task_id"])
        dependency_ids = [
            item for item in _load_list(task.get("prerequisites")) if item in task_to_step
        ]
        if not dependency_ids and position > 0:
            dependency_ids = [str(ordered[position - 1]["task_id"])]
        for dependency_id in dependency_ids:
            conn.execute(
                """INSERT OR IGNORE INTO task_step_dependencies
                   (run_id, step_id, depends_on_step_id) VALUES (?, ?, ?)""",
                (run_id, task_to_step[task_id], task_to_step[dependency_id]),
            )
    _refresh_dependency_readiness(conn, user_id, run_id, now, emit_events=False)
    _sync_run_and_goal(conn, user_id, goal_id, run_id, now, reason="legacy_chain_canonical_create")
    _event(
        conn,
        user_id,
        run_id,
        "legacy.chain_canonical_created",
        now,
        payload={"legacy_chain_id": chain_id, "task_count": len(ordered)},
    )
    return {"goal_id": goal_id, "run_id": run_id, "steps": task_to_step}


def append_chain_task_execution(
    conn: sqlite3.Connection,
    user_id: str,
    chain_id: str,
    tasks: Sequence[Mapping[str, Any]],
    now: str,
) -> Optional[Dict[str, Any]]:
    """Append canonical Steps to an existing legacy workflow before compatibility rows."""
    if not tasks:
        return None
    existing = conn.execute(
        """SELECT goal_id, run_id FROM legacy_chain_execution_links
           WHERE legacy_chain_id = ? AND user_id = ?""",
        (chain_id, user_id),
    ).fetchone()
    if existing is None:
        return None

    goal_id, run_id = str(existing["goal_id"]), str(existing["run_id"])
    linked_steps = {
        str(row["legacy_task_id"]): str(row["step_id"])
        for row in conn.execute(
            """SELECT legacy_task_id, step_id FROM legacy_task_execution_links
               WHERE legacy_chain_id = ? AND user_id = ?""",
            (chain_id, user_id),
        ).fetchall()
    }
    previous = conn.execute(
        """SELECT step_id FROM task_steps WHERE run_id = ? AND user_id = ?
           ORDER BY position DESC, created_at DESC LIMIT 1""",
        (run_id, user_id),
    ).fetchone()
    fallback_dependency = str(previous["step_id"]) if previous is not None else None
    ordered = sorted(
        tasks,
        key=lambda item: (int(item.get("chain_order") or 0), str(item.get("created_at") or "")),
    )
    added: Dict[str, str] = {}
    for task in ordered:
        task_id = str(task["task_id"])
        if task_id in linked_steps:
            raise RuntimeError("Task already has a canonical workflow Step")
        step_id = _insert_step(
            conn,
            user_id,
            goal_id,
            run_id,
            task,
            now,
            position=max(0, int(task.get("chain_order") or 1) - 1),
            chain_id=chain_id,
            link_legacy_task=False,
        )
        linked_steps[task_id] = step_id
        added[task_id] = step_id

    previous_added_step = fallback_dependency
    for task in ordered:
        task_id = str(task["task_id"])
        dependency_ids = [
            item for item in _load_list(task.get("prerequisites")) if item in linked_steps
        ]
        if not dependency_ids and previous_added_step is not None:
            conn.execute(
                """INSERT OR IGNORE INTO task_step_dependencies
                   (run_id, step_id, depends_on_step_id) VALUES (?, ?, ?)""",
                (run_id, added[task_id], previous_added_step),
            )
        else:
            for dependency_id in dependency_ids:
                conn.execute(
                    """INSERT OR IGNORE INTO task_step_dependencies
                       (run_id, step_id, depends_on_step_id) VALUES (?, ?, ?)""",
                    (run_id, added[task_id], linked_steps[dependency_id]),
                )
        previous_added_step = added[task_id]

    _refresh_dependency_readiness(conn, user_id, run_id, now, emit_events=True)
    _sync_run_and_goal(
        conn, user_id, goal_id, run_id, now, reason="legacy_chain_canonical_extend"
    )
    _event(
        conn,
        user_id,
        run_id,
        "legacy.chain_canonical_extended",
        now,
        payload={"legacy_chain_id": chain_id, "added": len(added)},
    )
    return {"goal_id": goal_id, "run_id": run_id, "steps": added}

def project_standalone_task(
    conn: sqlite3.Connection, user_id: str, task: Mapping[str, Any], now: str
) -> Dict[str, str]:
    task_id = str(task["task_id"])
    existing = conn.execute(
        """SELECT goal_id, run_id, step_id FROM legacy_task_execution_links
           WHERE legacy_task_id = ? AND user_id = ?""",
        (task_id, user_id),
    ).fetchone()
    if existing is not None:
        return dict(existing)
    legacy_status = _legacy_step_status(str(task.get("status") or "pending"))
    title = str(task.get("task_name") or "Legacy task")
    description = str(task.get("description") or "")
    goal_id = _insert_goal(
        conn,
        user_id,
        title,
        description,
        str(task.get("priority") or "medium"),
        {"legacy_task_id": task_id},
        now,
        completed=legacy_status == "completed",
    )
    run_id = str(uuid.uuid4())
    run_status = _run_status([legacy_status])
    started_at, completed_at = _timestamps(run_status, now)
    conn.execute(
        """INSERT INTO task_runs
           (run_id, goal_id, user_id, title, objective, mode, status, version,
            idempotency_key, metadata, created_at, updated_at, started_at, completed_at, error_summary)
           VALUES (?, ?, ?, ?, ?, 'manual', ?, 1, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            goal_id,
            user_id,
            title,
            description,
            run_status,
            f"legacy-task:{task_id}",
            _json({"legacy_task_id": task_id}),
            now,
            now,
            started_at,
            completed_at,
            "Legacy task failed" if run_status == "failed" else None,
        ),
    )
    step_id = _insert_step(
        conn, user_id, goal_id, run_id, task, now, position=0, chain_id=None
    )
    _refresh_dependency_readiness(conn, user_id, run_id, now, emit_events=False)
    _event(
        conn,
        user_id,
        run_id,
        "legacy.task_projected",
        now,
        step_id=step_id,
        payload={"legacy_task_id": task_id},
    )
    return {"goal_id": goal_id, "run_id": run_id, "step_id": step_id}


def project_chain(
    conn: sqlite3.Connection,
    user_id: str,
    chain: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
    now: str,
) -> Optional[Dict[str, str]]:
    if not tasks:
        return None
    chain_id = str(chain["chain_id"])
    ordered = sorted(
        tasks,
        key=lambda item: (int(item.get("chain_order") or 0), str(item.get("created_at") or "")),
    )
    existing = conn.execute(
        """SELECT goal_id, run_id FROM legacy_chain_execution_links
           WHERE legacy_chain_id = ? AND user_id = ?""",
        (chain_id, user_id),
    ).fetchone()
    created_run = existing is None
    if created_run:
        statuses = [_legacy_step_status(str(task.get("status") or "pending")) for task in ordered]
        run_status = _run_status(statuses)
        title = str(chain.get("chain_name") or "Legacy workflow")
        description = str(chain.get("description") or "")
        goal_id = _insert_goal(
            conn,
            user_id,
            title,
            description,
            str(ordered[0].get("priority") or "medium"),
            {"legacy_chain_id": chain_id},
            now,
            completed=run_status == "completed",
        )
        run_id = str(uuid.uuid4())
        started_at, completed_at = _timestamps(run_status, now)
        conn.execute(
            """INSERT INTO task_runs
               (run_id, goal_id, user_id, title, objective, mode, status, version,
                idempotency_key, metadata, created_at, updated_at, started_at, completed_at, error_summary)
               VALUES (?, ?, ?, ?, ?, 'manual', ?, 1, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                goal_id,
                user_id,
                title,
                description,
                run_status,
                f"legacy-chain:{chain_id}",
                _json({"legacy_chain_id": chain_id}),
                now,
                now,
                started_at,
                completed_at,
                "Legacy workflow failed" if run_status == "failed" else None,
            ),
        )
        conn.execute(
            """INSERT INTO legacy_chain_execution_links
               (legacy_chain_id, user_id, goal_id, run_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (chain_id, user_id, goal_id, run_id, now),
        )
    else:
        goal_id, run_id = existing["goal_id"], existing["run_id"]

    task_to_step = {
        row["legacy_task_id"]: row["step_id"]
        for row in conn.execute(
            """SELECT legacy_task_id, step_id FROM legacy_task_execution_links
               WHERE legacy_chain_id = ? AND user_id = ?""",
            (chain_id, user_id),
        ).fetchall()
    }
    added = 0
    for position, task in enumerate(ordered):
        task_id = str(task["task_id"])
        if task_id in task_to_step:
            conn.execute(
                "UPDATE task_steps SET position = ?, updated_at = ? WHERE step_id = ?",
                (position, now, task_to_step[task_id]),
            )
            continue
        task_to_step[task_id] = _insert_step(
            conn,
            user_id,
            goal_id,
            run_id,
            task,
            now,
            position=position,
            chain_id=chain_id,
        )
        added += 1

    for position, task in enumerate(ordered):
        task_id = str(task["task_id"])
        dependency_ids = [
            item for item in _load_list(task.get("prerequisites")) if item in task_to_step
        ]
        if not dependency_ids and position > 0:
            dependency_ids = [str(ordered[position - 1]["task_id"])]
        for dependency_id in dependency_ids:
            conn.execute(
                """INSERT OR IGNORE INTO task_step_dependencies
                   (run_id, step_id, depends_on_step_id) VALUES (?, ?, ?)""",
                (run_id, task_to_step[task_id], task_to_step[dependency_id]),
            )

    _refresh_dependency_readiness(conn, user_id, run_id, now, emit_events=not created_run)
    _sync_run_and_goal(
        conn, user_id, goal_id, run_id, now, reason="legacy_chain_projection"
    )
    if created_run or added:
        _event(
            conn,
            user_id,
            run_id,
            "legacy.chain_projected" if created_run else "legacy.chain_extended",
            now,
            payload={"legacy_chain_id": chain_id, "task_count": len(ordered), "added": added},
        )
    return {"goal_id": goal_id, "run_id": run_id}


def ensure_task_projection(
    conn: sqlite3.Connection, user_id: str, task_id: str, now: str
) -> Optional[Dict[str, str]]:
    existing = conn.execute(
        """SELECT goal_id, run_id, step_id FROM legacy_task_execution_links
           WHERE legacy_task_id = ? AND user_id = ?""",
        (task_id, user_id),
    ).fetchone()
    if existing is not None:
        return dict(existing)
    task_row = conn.execute(
        "SELECT * FROM tasks WHERE task_id = ? AND user_id = ?", (task_id, user_id)
    ).fetchone()
    if task_row is None:
        return None
    task = dict(task_row)
    chain_id = task.get("chain_id")
    if chain_id:
        chain_row = conn.execute(
            "SELECT * FROM task_chains WHERE chain_id = ? AND user_id = ?",
            (chain_id, user_id),
        ).fetchone()
        if chain_row is not None:
            tasks = [
                dict(row)
                for row in conn.execute(
                    """SELECT * FROM tasks WHERE chain_id = ? AND user_id = ?
                       ORDER BY chain_order, created_at""",
                    (chain_id, user_id),
                ).fetchall()
            ]
            project_chain(conn, user_id, dict(chain_row), tasks, now)
            linked = conn.execute(
                """SELECT goal_id, run_id, step_id FROM legacy_task_execution_links
                   WHERE legacy_task_id = ? AND user_id = ?""",
                (task_id, user_id),
            ).fetchone()
            return dict(linked) if linked is not None else None
    return project_standalone_task(conn, user_id, task, now)


def sync_task_status(
    conn: sqlite3.Connection, user_id: str, task_id: str, legacy_status: str, now: str
) -> bool:
    link = ensure_task_projection(conn, user_id, task_id, now)
    if link is None:
        return False
    run_id, step_id, goal_id = link["run_id"], link["step_id"], link["goal_id"]
    current = conn.execute(
        "SELECT status FROM task_steps WHERE step_id = ? AND user_id = ?",
        (step_id, user_id),
    ).fetchone()
    if current is None:
        return False
    target = _legacy_step_status(legacy_status)
    changed = current["status"] != target
    if changed:
        assignments = ["status = ?", "updated_at = ?"]
        params: list[Any] = [target, now]
        if target == "running":
            assignments.extend(
                ["attempt_count = attempt_count + 1", "started_at = COALESCE(started_at, ?)"]
            )
            params.append(now)
        if target == "waiting_approval":
            assignments.extend(["requires_approval = 1", "started_at = COALESCE(started_at, ?)"])
            params.append(now)
        if target == "completed":
            assignments.extend(["progress = 100", "completed_at = COALESCE(completed_at, ?)"])
            params.append(now)
        elif current["status"] == "completed":
            assignments.append("completed_at = NULL")
        if target == "failed":
            assignments.append("error_summary = 'Legacy task failed'")
        else:
            assignments.append("error_summary = NULL")
        params.extend((step_id, user_id))
        conn.execute(
            f"UPDATE task_steps SET {', '.join(assignments)} WHERE step_id = ? AND user_id = ?",
            params,
        )
        _event(
            conn,
            user_id,
            run_id,
            f"legacy.task.{legacy_status}",
            now,
            step_id=step_id,
            payload={"legacy_task_id": task_id},
        )
    if target == "waiting_approval":
        _ensure_pending_approval(conn, user_id, run_id, step_id, task_id, now)
    elif target == "completed":
        _resolve_pending_approvals(
            conn, user_id, run_id, step_id, task_id, "approved", now
        )
    elif target == "failed":
        _resolve_pending_approvals(
            conn, user_id, run_id, step_id, task_id, "rejected", now
        )
    else:
        _resolve_pending_approvals(
            conn, user_id, run_id, step_id, task_id, "cancelled", now
        )
    _refresh_dependency_readiness(conn, user_id, run_id, now, emit_events=True)
    _sync_run_and_goal(conn, user_id, goal_id, run_id, now, reason=f"legacy_task:{task_id}")
    return changed


def sync_task_progress(
    conn: sqlite3.Connection, user_id: str, task_id: str, progress: int, now: str
) -> bool:
    link = ensure_task_projection(conn, user_id, task_id, now)
    if link is None:
        return False
    normalized = max(0, min(100, int(progress)))
    cursor = conn.execute(
        "UPDATE task_steps SET progress = ?, updated_at = ? WHERE step_id = ? AND user_id = ?",
        (normalized, now, link["step_id"], user_id),
    )
    if cursor.rowcount > 0:
        _event(
            conn,
            user_id,
            str(link["run_id"]),
            "legacy.task.progress_updated",
            now,
            step_id=str(link["step_id"]),
            payload={"legacy_task_id": task_id, "progress": normalized},
        )
    return cursor.rowcount > 0


def delete_task_projection(conn: sqlite3.Connection, user_id: str, task_id: str, now: str) -> None:
    link = conn.execute(
        """SELECT * FROM legacy_task_execution_links
           WHERE legacy_task_id = ? AND user_id = ?""",
        (task_id, user_id),
    ).fetchone()
    if link is None:
        return
    if link["legacy_chain_id"] is None:
        conn.execute(
            "DELETE FROM task_goals WHERE goal_id = ? AND user_id = ?",
            (link["goal_id"], user_id),
        )
        return
    conn.execute(
        "DELETE FROM task_steps WHERE step_id = ? AND user_id = ?", (link["step_id"], user_id)
    )
    remaining = conn.execute(
        "SELECT 1 FROM task_steps WHERE run_id = ? AND user_id = ? LIMIT 1",
        (link["run_id"], user_id),
    ).fetchone()
    if remaining is None:
        conn.execute(
            "DELETE FROM task_goals WHERE goal_id = ? AND user_id = ?",
            (link["goal_id"], user_id),
        )
        return
    _refresh_dependency_readiness(conn, user_id, link["run_id"], now, emit_events=True)
    _sync_run_and_goal(
        conn,
        user_id,
        link["goal_id"],
        link["run_id"],
        now,
        reason=f"legacy_task_deleted:{task_id}",
    )


def delete_chain_projection(conn: sqlite3.Connection, user_id: str, chain_id: str) -> None:
    link = conn.execute(
        """SELECT goal_id FROM legacy_chain_execution_links
           WHERE legacy_chain_id = ? AND user_id = ?""",
        (chain_id, user_id),
    ).fetchone()
    if link is not None:
        conn.execute(
            "DELETE FROM task_goals WHERE goal_id = ? AND user_id = ?",
            (link["goal_id"], user_id),
        )


def backfill_legacy_task_execution(conn: sqlite3.Connection, now: str) -> None:
    chains = conn.execute("SELECT * FROM task_chains ORDER BY created_at").fetchall()
    for chain_row in chains:
        chain = dict(chain_row)
        tasks = [
            dict(row)
            for row in conn.execute(
                """SELECT * FROM tasks WHERE chain_id = ? AND user_id = ?
                   ORDER BY chain_order, created_at""",
                (chain["chain_id"], chain["user_id"]),
            ).fetchall()
        ]
        project_chain(conn, chain["user_id"], chain, tasks, now)
    standalone = conn.execute(
        """SELECT t.* FROM tasks t
           LEFT JOIN legacy_task_execution_links l ON l.legacy_task_id = t.task_id
           WHERE l.legacy_task_id IS NULL ORDER BY t.created_at"""
    ).fetchall()
    for task_row in standalone:
        task = dict(task_row)
        project_standalone_task(conn, task["user_id"], task, now)
