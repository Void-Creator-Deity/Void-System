"""SQLite persistence for reviewable plan drafts and atomic Goal/Run publication."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from adapters.sqlite.object_json import decode_object, encode_object


ConnectionFactory = Callable[[], sqlite3.Connection]


def _now() -> str:
    """Return a sortable UTC timestamp for draft and publication records."""
    return datetime.now(timezone.utc).isoformat()


def _decode(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Decode the persisted Plan Draft JSON payload into its authoritative API snapshot."""
    if row is None:
        return None
    value = dict(row)
    value["payload"] = decode_object(value.get("payload"))
    value["version"] = int(value.get("version") or 1)
    return value


class SQLitePlanDraftRepository:
    """Persist owner-scoped Plan Drafts and publish them in one SQLite transaction.

    Inputs:
        connection_factory: Opens application-configured SQLite connections.
    Outputs:
        Draft snapshots and published Goal/Run identifiers; all reads are owner-scoped.
    Called by:
        PlanGenerationRepository when a worker finishes, and PlanDraftService for user editing
        and publication.
    Side effects:
        Creates draft records, increments optimistic versions, and atomically inserts Goal, Run,
        Step, dependency, and Event records during publication.
    Failure:
        SQLite failures are propagated. A false update result represents a concurrent change;
        callers translate it into a stable state conflict.
    Invariants:
        One generation owns at most one draft. A draft is published at most once, and the same
        user plus idempotency key always resolves to the same Goal/Run pair.
    """

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def create_from_generation(self, user_id: str, generation_id: str, payload: Mapping[str, Any], *, conn: Optional[sqlite3.Connection] = None, now: Optional[str] = None) -> Dict[str, Any]:
        """Create or reuse a draft for one completed generation.

        Inputs:
            user_id: Draft owner; generation_id: durable source job; payload: generated plan object.
            conn: Optional caller-owned transaction used by PlanGenerationRepository.
        Outputs:
            The authoritative persisted draft snapshot.
        Called by:
            PlanGenerationRepository._finish while publishing a ready generation job.
        Side effects:
            Inserts plan_drafts and stores the full generation result as JSON when no draft exists.
        Failure:
            Raises SQLite errors. Existing generation records are returned rather than duplicated.
        Invariants:
            The source generation is unique globally and a generated payload is never written to a
            different owner.
        """
        owns_connection = conn is None
        connection = conn or self._connection_factory()
        created_at = now or _now()
        try:
            existing = _decode(connection.execute("SELECT * FROM plan_drafts WHERE generation_id = ?", (generation_id,)).fetchone())
            if existing is not None:
                if existing["user_id"] != user_id:
                    raise ValueError("Plan generation owner mismatch")
                return existing
            draft_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO plan_drafts
                   (draft_id, user_id, generation_id, payload, status, version, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'ready', 1, ?, ?)""",
                (draft_id, user_id, generation_id, encode_object(payload), created_at, created_at),
            )
            row = _decode(connection.execute("SELECT * FROM plan_drafts WHERE draft_id = ?", (draft_id,)).fetchone())
            if row is None:
                raise RuntimeError("Plan draft insert was not readable")
            if owns_connection:
                connection.commit()
            return row
        except Exception:
            if owns_connection:
                connection.rollback()
            raise
        finally:
            if owns_connection:
                connection.close()

    def get(self, user_id: str, draft_id: str) -> Optional[Dict[str, Any]]:
        """Read one owner-scoped persisted draft without exposing other users' history."""
        conn = self._connection_factory()
        try:
            return _decode(conn.execute("SELECT * FROM plan_drafts WHERE draft_id = ? AND user_id = ?", (draft_id, user_id)).fetchone())
        finally:
            conn.close()

    def list_recent(self, user_id: str, *, limit: int = 30) -> Sequence[Dict[str, Any]]:
        """List the caller's recent drafts for refresh recovery and the plan workspace."""
        conn = self._connection_factory()
        try:
            rows = conn.execute("SELECT * FROM plan_drafts WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?", (user_id, max(1, min(100, int(limit))))).fetchall()
            return [item for row in rows if (item := _decode(row)) is not None]
        finally:
            conn.close()

    def update(self, user_id: str, draft_id: str, payload: Mapping[str, Any], expected_version: int) -> Optional[Dict[str, Any]]:
        """Replace a ready draft after an optimistic-version check.

        Inputs:
            owner, draft id, normalized full plan payload, and the version rendered by the client.
        Outputs:
            Updated authoritative draft or None when it was missing, published, or concurrently changed.
        Called by:
            PlanDraftService.update from the first-party Advisor editor.
        Side effects:
            Replaces JSON payload and increments version inside an immediate transaction.
        Failure:
            SQLite failures roll back. Version races are intentionally non-exceptional and return None.
        Invariants:
            Only ready drafts can change; updates never mutate published Goal or Run records.
        """
        conn, now = self._connection_factory(), _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            changed = conn.execute(
                """UPDATE plan_drafts SET payload = ?, version = version + 1, updated_at = ?
                   WHERE draft_id = ? AND user_id = ? AND status = 'ready' AND version = ?""",
                (encode_object(payload), now, draft_id, user_id, expected_version),
            )
            if changed.rowcount != 1:
                conn.rollback()
                return None
            row = _decode(conn.execute("SELECT * FROM plan_drafts WHERE draft_id = ? AND user_id = ?", (draft_id, user_id)).fetchone())
            conn.commit()
            return row
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def publish(self, user_id: str, draft_id: str, idempotency_key: str, publication: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        """Atomically publish a validated draft as one active Goal and started Run.

        Inputs:
            owner, draft id, stable client retry key, and normalized goal/run publication spec.
        Outputs:
            Draft snapshot enriched with the canonical Goal and Run identifiers.
        Called by:
            PlanDraftService.publish after TaskExecution validates the editable draft payload.
        Side effects:
            In one transaction inserts Goal, Run, Steps, dependencies, initial events, then marks the
            draft published. The initial Run is running and dependency-free Steps are ready.
        Failure:
            Returns None for missing drafts. Raises ValueError for a conflicting publication key or a
            malformed already-validated dependency. SQLite errors roll back every inserted record.
        Invariants:
            One draft creates at most one Goal/Run pair. Repeating the same key returns that pair;
            no partially created execution records survive a failed publication.
        """
        conn, now = self._connection_factory(), _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            draft = _decode(conn.execute("SELECT * FROM plan_drafts WHERE draft_id = ? AND user_id = ?", (draft_id, user_id)).fetchone())
            if draft is None:
                conn.rollback()
                return None
            if draft["status"] == "published":
                if draft.get("publication_key") == idempotency_key:
                    conn.rollback()
                    return draft
                raise ValueError("PLAN_DRAFT_ALREADY_PUBLISHED")
            if draft["status"] != "ready":
                raise ValueError("PLAN_DRAFT_NOT_READY")
            key_owner = conn.execute("SELECT draft_id FROM plan_drafts WHERE user_id = ? AND publication_key = ? AND draft_id != ?", (user_id, idempotency_key, draft_id)).fetchone()
            if key_owner is not None:
                raise ValueError("PLAN_DRAFT_IDEMPOTENCY_CONFLICT")

            goal, run = dict(publication["goal"]), dict(publication["run"])
            steps = list(run.pop("steps"))
            goal_id, run_id = str(uuid.uuid4()), str(uuid.uuid4())
            source_metadata = {"source": "plan_draft", "plan_draft_id": draft_id, "generation_id": draft.get("generation_id")}
            goal_metadata = {**dict(goal.get("metadata") or {}), **source_metadata}
            run_metadata = {**dict(run.get("metadata") or {}), **source_metadata}
            stable_key = f"plan_draft:{draft_id}:{idempotency_key}"
            conn.execute(
                """INSERT INTO task_goals
                   (goal_id, user_id, title, description, desired_outcome, status, priority, idempotency_key, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)""",
                (goal_id, user_id, goal["title"], goal.get("description", ""), goal.get("desired_outcome", ""), goal.get("priority", "medium"), stable_key, encode_object(goal_metadata), now, now),
            )
            conn.execute(
                """INSERT INTO task_runs
                   (run_id, goal_id, user_id, title, objective, mode, status, version, idempotency_key, metadata, created_at, updated_at, started_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'running', 1, ?, ?, ?, ?, ?)""",
                (run_id, goal_id, user_id, run["title"], run.get("objective", ""), run.get("mode", "manual"), stable_key, encode_object(run_metadata), now, now, now),
            )
            key_to_id: Dict[str, str] = {}
            normalized_steps: list[tuple[str, str, Mapping[str, Any], int]] = []
            for position, step in enumerate(steps):
                client_key = str(step["client_key"])
                if client_key in key_to_id:
                    raise ValueError("PLAN_DRAFT_INVALID_STEP_GRAPH")
                step_id = str(uuid.uuid4())
                key_to_id[client_key] = step_id
                normalized_steps.append((step_id, client_key, step, position))
            for step_id, client_key, step, position in normalized_steps:
                ready = not list(step.get("depends_on") or [])
                conn.execute(
                    """INSERT INTO task_steps
                       (step_id, run_id, user_id, client_key, title, description, kind, status, position, parallel_group, attempt_count, max_attempts, requires_approval, progress, completion_criteria, input_data, output_data, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 0, ?, ?, '{}', ?, ?)""",
                    (step_id, run_id, user_id, client_key, step["title"], step.get("description", ""), step.get("kind", "manual"), "ready" if ready else "pending", position, step.get("parallel_group"), int(step.get("max_attempts", 1)), 1 if step.get("requires_approval") else 0, encode_object(step.get("completion_criteria") or {}), encode_object(step.get("input_data") or {}), now, now),
                )
            for step_id, _client_key, step, _position in normalized_steps:
                for dependency_key in list(step.get("depends_on") or []):
                    dependency_id = key_to_id.get(str(dependency_key))
                    if dependency_id is None or dependency_id == step_id:
                        raise ValueError("PLAN_DRAFT_INVALID_STEP_GRAPH")
                    conn.execute("INSERT INTO task_step_dependencies (run_id, step_id, depends_on_step_id) VALUES (?, ?, ?)", (run_id, step_id, dependency_id))
            for event_type, payload in (("run.created", {"step_count": len(steps), "source": "plan_draft"}), ("run.started", {"source": "plan_draft", "initial_ready_steps": sum(1 for _step_id, _key, step, _position in normalized_steps if not step.get("depends_on"))})):
                conn.execute("INSERT INTO task_events (event_id, run_id, user_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), run_id, user_id, event_type, encode_object(payload), now))
            conn.execute(
                """UPDATE plan_drafts SET status = 'published', publication_key = ?, published_goal_id = ?, published_run_id = ?, published_at = ?, updated_at = ?, version = version + 1
                   WHERE draft_id = ? AND user_id = ? AND status = 'ready'""",
                (idempotency_key, goal_id, run_id, now, now, draft_id, user_id),
            )
            row = _decode(conn.execute("SELECT * FROM plan_drafts WHERE draft_id = ? AND user_id = ?", (draft_id, user_id)).fetchone())
            conn.commit()
            return row
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
