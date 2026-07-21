"""SQLite persistence for durable asynchronous plan-generation jobs."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Mapping, Optional

from adapters.sqlite.plan_draft_repository import SQLitePlanDraftRepository

DEFAULT_LEASE_SECONDS = 15 * 60


def _now() -> str:
    """Return a lexically sortable UTC timestamp for SQLite state comparisons."""
    return datetime.now(timezone.utc).isoformat()


def _expiry(seconds: int) -> str:
    """Return a bounded worker-lease expiry in UTC."""
    return (datetime.now(timezone.utc) + timedelta(seconds=max(30, seconds))).isoformat()


def _decode(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Decode stored JSON fields into the repository's canonical job snapshot."""
    if row is None:
        return None
    item = dict(row)
    for field, fallback in (("advisor_prefs", {}), ("result", None)):
        try:
            item[field] = json.loads(item[field]) if item.get(field) is not None else fallback
        except (TypeError, json.JSONDecodeError):
            item[field] = fallback
    item["attempt_count"] = int(item.get("attempt_count") or 0)
    item["cancel_requested"] = bool(item.get("cancel_requested", False))
    return item


class SQLitePlanGenerationRepository:
    """Own owner-scoped plan job persistence and worker-lease state.

    Inputs:
        connection_factory: Opens SQLite connections configured by the application Database.
    Outputs:
        Durable job snapshots. Lease tokens are internal and must never be serialized to HTTP.
    Called by:
        PlanGenerationService and the application-owned PlanGenerationWorker.
    Side effects:
        Writes job lifecycle transitions, cancellation requests, and worker leases.
    Failure:
        Propagates SQLite failures; callers translate them into a retry or stable API error.
    Invariants:
        A non-expired (worker_id, lease_token) pair is required to advance a generating job.
        All public reads remain owner-scoped.
    """

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def create(self, user_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        """Persist one queued request and return its authoritative snapshot."""
        generation_id, now = str(uuid.uuid4()), _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO plan_generation_jobs
                   (generation_id, user_id, topic, execution_mode, max_steps, advisor_prefs,
                    status, stage, progress, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'queued', 'queued', 0, ?, ?)""",
                (generation_id, user_id, values["topic"], values["execution_mode"],
                 values["max_steps"], json.dumps(values.get("advisor_prefs") or {}, ensure_ascii=False),
                 now, now),
            )
            conn.commit()
            return self.get(user_id, generation_id) or {}
        finally:
            conn.close()

    def get(self, user_id: str, generation_id: str) -> Optional[Dict[str, Any]]:
        """Read one owner-scoped generation job."""
        conn = self._connection_factory()
        try:
            return _decode(conn.execute(
                "SELECT * FROM plan_generation_jobs WHERE generation_id = ? AND user_id = ?",
                (generation_id, user_id),
            ).fetchone())
        finally:
            conn.close()

    def list_recent(self, user_id: str, *, limit: int = 20) -> list[Dict[str, Any]]:
        """Return recent owner jobs for refresh recovery and the progress center."""
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM plan_generation_jobs WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, max(1, min(100, int(limit)))),
            ).fetchall()
            return [item for row in rows if (item := _decode(row)) is not None]
        finally:
            conn.close()

    def recover_interrupted_jobs(self) -> int:
        """Requeue stranded work during application startup.

        Inputs:
            None. The current process may no longer own any persisted running lease.
        Outputs:
            Number of affected jobs.
        Called by:
            FastAPI lifespan before the worker starts.
        Side effects:
            Clears leases; cancellation requests become terminal, other jobs restart from queued.
        Failure:
            Rolls back all recovery writes on SQLite error.
        Invariants:
            No partial model output is published after a process loss.
        """
        conn, now = self._connection_factory(), _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cancelled = conn.execute(
                """UPDATE plan_generation_jobs
                   SET status = 'cancelled', stage = 'cancelled', completed_at = ?,
                       worker_id = NULL, lease_token = NULL, lease_expires_at = NULL,
                       heartbeat_at = NULL, updated_at = ?
                   WHERE status = 'generating' AND cancel_requested = 1""", (now, now))
            requeued = conn.execute(
                """UPDATE plan_generation_jobs
                   SET status = 'queued', stage = 'queued', progress = 0,
                       worker_id = NULL, lease_token = NULL, lease_expires_at = NULL,
                       heartbeat_at = NULL, updated_at = ?
                   WHERE status = 'generating' AND cancel_requested = 0""", (now,))
            conn.commit()
            return int(cancelled.rowcount) + int(requeued.rowcount)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def claim(self, user_id: str, generation_id: str, *, worker_id: str = "test-worker",
              lease_seconds: int = DEFAULT_LEASE_SECONDS) -> Optional[Dict[str, Any]]:
        """Claim an addressed owner job; used by focused tests and manual worker control."""
        return self._claim(
            "generation_id = ? AND user_id = ?", (generation_id, user_id), worker_id, lease_seconds
        )

    def claim_next(self, worker_id: str, *, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> Optional[Dict[str, Any]]:
        """Atomically lease the oldest queued or expired job for one worker."""
        now = _now()
        return self._claim(
            "status = 'queued' OR (status = 'generating' AND lease_expires_at IS NOT NULL "
            "AND lease_expires_at <= ?)", (now,), worker_id, lease_seconds
        )

    def _claim(self, where: str, values: tuple[Any, ...], worker_id: str,
               lease_seconds: int) -> Optional[Dict[str, Any]]:
        conn, now, token = self._connection_factory(), _now(), str(uuid.uuid4())
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT generation_id FROM plan_generation_jobs WHERE cancel_requested = 0 AND (" + where +
                ") ORDER BY created_at ASC LIMIT 1", values,
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            generation_id = str(row["generation_id"])
            updated = conn.execute(
                """UPDATE plan_generation_jobs
                   SET status = 'generating', stage = 'preparing_context', progress = 10,
                       started_at = COALESCE(started_at, ?), worker_id = ?, lease_token = ?,
                       lease_expires_at = ?, heartbeat_at = ?, attempt_count = attempt_count + 1,
                       updated_at = ?
                   WHERE generation_id = ? AND cancel_requested = 0
                     AND (status = 'queued' OR (status = 'generating' AND lease_expires_at <= ?))""",
                (now, worker_id, token, _expiry(lease_seconds), now, now, generation_id, now),
            )
            if not updated.rowcount:
                conn.commit()
                return None
            snapshot = _decode(conn.execute(
                "SELECT * FROM plan_generation_jobs WHERE generation_id = ?", (generation_id,)
            ).fetchone())
            conn.commit()
            return snapshot
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def heartbeat(self, generation_id: str, worker_id: str, lease_token: str,
                  *, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> bool:
        """Renew a current lease before a bounded generation stage begins."""
        conn, now = self._connection_factory(), _now()
        try:
            changed = conn.execute(
                """UPDATE plan_generation_jobs SET heartbeat_at = ?, lease_expires_at = ?, updated_at = ?
                   WHERE generation_id = ? AND status = 'generating' AND cancel_requested = 0
                     AND worker_id = ? AND lease_token = ? AND lease_expires_at > ?""",
                (now, _expiry(lease_seconds), now, generation_id, worker_id, lease_token, now),
            )
            conn.commit()
            return bool(changed.rowcount)
        finally:
            conn.close()

    def is_cancel_requested(self, generation_id: str, worker_id: str, lease_token: str) -> bool:
        """Read cooperative cancellation state for the active leased worker only."""
        conn = self._connection_factory()
        try:
            row = conn.execute(
                """SELECT cancel_requested FROM plan_generation_jobs
                   WHERE generation_id = ? AND status = 'generating'
                     AND worker_id = ? AND lease_token = ?""",
                (generation_id, worker_id, lease_token),
            ).fetchone()
            return row is None or bool(row["cancel_requested"])
        finally:
            conn.close()

    def update_progress(self, generation_id: str, worker_id: str, lease_token: str,
                        stage: str, progress: int) -> bool:
        """Write a progress checkpoint only while the worker still owns its lease."""
        conn, now = self._connection_factory(), _now()
        try:
            changed = conn.execute(
                """UPDATE plan_generation_jobs SET stage = ?, progress = ?, updated_at = ?
                   WHERE generation_id = ? AND status = 'generating' AND cancel_requested = 0
                     AND worker_id = ? AND lease_token = ? AND lease_expires_at > ?""",
                (stage, max(0, min(99, int(progress))), now, generation_id, worker_id, lease_token, now),
            )
            conn.commit()
            return bool(changed.rowcount)
        finally:
            conn.close()

    def complete(self, generation_id: str, worker_id: str, lease_token: str,
                 result: Mapping[str, Any]) -> bool:
        """Publish a draft iff the current worker still holds the job lease and no cancel raced it."""
        return self._finish(generation_id, worker_id, lease_token, result=result, error=None)

    def fail(self, generation_id: str, worker_id: str, lease_token: str, message: str) -> bool:
        """Finalize a job failure, preserving a racing cancellation as cancelled instead."""
        return self._finish(generation_id, worker_id, lease_token, result=None, error=message)

    def _finish(self, generation_id: str, worker_id: str, lease_token: str,
                *, result: Optional[Mapping[str, Any]], error: Optional[str]) -> bool:
        """Finalize a worker claim without allowing cancellation or lease races to publish output.

        Inputs:
            generation_id, worker lease pair, and exactly one of a generated result or safe error text.
        Outputs:
            True only when a ready or failed terminal state owned by this worker was persisted.
        Called by:
            complete and fail after PlanGenerationService finishes an application-owned worker job.
        Side effects:
            Creates the owner-scoped Plan Draft in the same SQLite transaction as a ready Job update,
            or records a terminal failed/cancelled state while clearing the private lease.
        Failure:
            SQLite failures roll back both draft and job changes. A stale/cancelled worker returns False.
        Invariants:
            A result is never published without a persisted draft reference, and late workers cannot
            overwrite a reclaimed lease or a cancellation request.
        """
        conn, now = self._connection_factory(), _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                """SELECT generation_id, user_id, status, cancel_requested
                   FROM plan_generation_jobs
                   WHERE generation_id = ? AND status = 'generating'
                     AND worker_id = ? AND lease_token = ?""",
                (generation_id, worker_id, lease_token),
            ).fetchone()
            if current is None:
                conn.rollback()
                return False
            if bool(current["cancel_requested"]):
                conn.execute(
                    """UPDATE plan_generation_jobs
                       SET status = 'cancelled', stage = 'cancelled', completed_at = ?,
                           worker_id = NULL, lease_token = NULL, lease_expires_at = NULL,
                           heartbeat_at = NULL, updated_at = ?
                       WHERE generation_id = ? AND worker_id = ? AND lease_token = ?""",
                    (now, now, generation_id, worker_id, lease_token),
                )
                conn.commit()
                return False
            if result is not None:
                draft = SQLitePlanDraftRepository(self._connection_factory).create_from_generation(
                    str(current["user_id"]), generation_id, result, conn=conn, now=now
                )
                changed = conn.execute(
                    """UPDATE plan_generation_jobs
                       SET status = 'ready', stage = 'ready', progress = 100, result = ?,
                           draft_id = ?, error_message = NULL, completed_at = ?, worker_id = NULL,
                           lease_token = NULL, lease_expires_at = NULL, heartbeat_at = NULL, updated_at = ?
                       WHERE generation_id = ? AND status = 'generating' AND cancel_requested = 0
                         AND worker_id = ? AND lease_token = ?""",
                    (json.dumps(dict(result), ensure_ascii=False), draft["draft_id"], now, now,
                     generation_id, worker_id, lease_token),
                )
                expected_status = "ready"
            else:
                changed = conn.execute(
                    """UPDATE plan_generation_jobs
                       SET status = 'failed', stage = 'failed', error_message = ?, completed_at = ?,
                           worker_id = NULL, lease_token = NULL, lease_expires_at = NULL,
                           heartbeat_at = NULL, updated_at = ?
                       WHERE generation_id = ? AND status = 'generating' AND cancel_requested = 0
                         AND worker_id = ? AND lease_token = ?""",
                    (error, now, now, generation_id, worker_id, lease_token),
                )
                expected_status = "failed"
            final_row = conn.execute(
                "SELECT status FROM plan_generation_jobs WHERE generation_id = ?", (generation_id,)
            ).fetchone()
            conn.commit()
            return bool(changed.rowcount) and final_row is not None and final_row["status"] == expected_status
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def cancel(self, user_id: str, generation_id: str) -> Optional[Dict[str, Any]]:
        """Cancel queued work immediately and request cooperative cancellation for active model calls.

        Outputs:
            The job becomes cancelled or cancelling; callers poll the same durable snapshot.
        Called by:
            Plan-generation DELETE endpoint and future global background-task controls.
        Side effects:
            Writes either a terminal cancellation or cancel_requested flag.
        Invariants:
            A cancellation can never be overwritten by a late worker completion.
        """
        conn, now = self._connection_factory(), _now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status FROM plan_generation_jobs WHERE generation_id = ? AND user_id = ?",
                (generation_id, user_id),
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            if row["status"] == "queued":
                conn.execute(
                    """UPDATE plan_generation_jobs SET status = 'cancelled', stage = 'cancelled',
                       cancel_requested = 1, completed_at = ?, updated_at = ?
                       WHERE generation_id = ? AND user_id = ?""", (now, now, generation_id, user_id))
            elif row["status"] == "generating":
                conn.execute(
                    """UPDATE plan_generation_jobs SET cancel_requested = 1, stage = 'cancelling',
                       updated_at = ? WHERE generation_id = ? AND user_id = ?""", (now, generation_id, user_id))
            conn.commit()
            return self.get(user_id, generation_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
