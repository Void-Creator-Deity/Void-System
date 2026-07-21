"""SQLite persistence for personal-knowledge lifecycle and durable jobs."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence


DEFAULT_LEASE_SECONDS = 15 * 60
_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _now() -> str:
    """Return a lexically sortable UTC timestamp for SQLite comparisons."""
    return datetime.now(timezone.utc).isoformat()


def _expiry(seconds: int) -> str:
    """Return a bounded UTC expiry time for a worker lease."""
    return (datetime.now(timezone.utc) + timedelta(seconds=max(30, seconds))).isoformat()


def _decode_json(value: Optional[str], fallback: Any) -> Any:
    """Decode one persisted JSON column without leaking malformed historical data."""
    try:
        return json.loads(value) if value else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _decode_job(row: Optional[sqlite3.Row], *, include_lease: bool = False) -> Optional[Dict[str, Any]]:
    """Convert a database job row into the canonical public or worker snapshot."""
    if row is None:
        return None
    item = dict(row)
    item["result"] = _decode_json(item.get("result"), None)
    item["chunk_count"] = int(item["chunk_count"]) if item.get("chunk_count") is not None else None
    item["progress"] = max(0, min(100, int(item.get("progress") or 0)))
    item["attempt_count"] = max(0, int(item.get("attempt_count") or 0))
    item["cancel_requested"] = bool(item.get("cancel_requested", False))
    if not include_lease:
        item.pop("lease_token", None)
    return item


class SQLiteKnowledgeLifecycleRepository:
    """Own personal-knowledge history and durable ingestion/rebuild job state.

    Inputs:
        connection_factory: Opens application-configured SQLite connections.
    Outputs:
        Owner-scoped public job snapshots and worker-only snapshots with a lease token.
    Called by:
        KnowledgeJobService, KnowledgeWorkspace document reads, and KnowledgeEngine traces.
    Side effects:
        Persists lifecycle records, worker leases, cancellation requests, results, and retrieval traces.
    Failure:
        Propagates SQLite failures so HTTP or worker callers can present one recoverable result.
    Invariants:
        Only a current worker lease advances an active job. Browser reads never receive lease tokens.
        Retrying creates a new job; terminal history is never rewritten.
    """

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def start_ingestion(
        self,
        *,
        document_id: str,
        owner_id: str,
        content_fingerprint: str,
        source_size: int,
        index_version: str,
        job_type: str = "ingest",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Create a queued job and version record for one stored document source.

        Inputs:
            document_id, owner_id: The source document and its authorization boundary.
            content_fingerprint/source_size: Immutable source-version identity.
            job_type: Either ingest for a new upload or rebuild for an existing source.
            force: Allows rebuild to create a new version even when source bytes match history.
        Outputs:
            Durable public job snapshot with version_id, job_id, and duplicate marker.
        Called by:
            PersonalKnowledgeDocumentManager after source persistence and KnowledgeJobService for rebuild/retry.
        Side effects:
            Inserts the document version and queued job in one SQLite transaction.
        Failure:
            Raises SQLite errors; no in-memory job is created as a fallback.
        Invariants:
            A non-forced duplicate source never starts a second ingestion job.
        """
        normalized_type = str(job_type or "ingest").strip().lower()
        if normalized_type not in {"ingest", "rebuild"}:
            raise ValueError("Knowledge job type must be ingest or rebuild")
        connection = self._connection_factory()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if not force:
                existing = connection.execute(
                    """SELECT version_id FROM knowledge_document_versions
                       WHERE document_id = ? AND owner_id = ? AND content_fingerprint = ?
                       ORDER BY created_at DESC LIMIT 1""",
                    (document_id, owner_id, content_fingerprint),
                ).fetchone()
                if existing:
                    connection.commit()
                    return {"version_id": existing[0], "job_id": None, "duplicate": True}

            now = _now()
            version_id = str(uuid.uuid4())
            job_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO knowledge_document_versions
                   (version_id, document_id, owner_id, content_fingerprint, source_size, index_version, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (version_id, document_id, owner_id, content_fingerprint, source_size, index_version, now),
            )
            connection.execute(
                """INSERT INTO knowledge_ingestion_jobs
                   (job_id, version_id, document_id, owner_id, job_type, status, stage, progress,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'queued', 'queued', 0, ?, ?)""",
                (job_id, version_id, document_id, owner_id, normalized_type, now, now),
            )
            connection.commit()
            result = self.get_job(owner_id, job_id) or {}
            result["duplicate"] = False
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_job(self, owner_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Read one public owner-scoped durable knowledge job."""
        connection = self._connection_factory()
        try:
            row = connection.execute(
                """SELECT jobs.*, documents.title AS document_title, documents.original_name AS document_name
                   FROM knowledge_ingestion_jobs AS jobs
                   LEFT JOIN user_documents AS documents ON documents.doc_id = jobs.document_id AND documents.user_id = jobs.owner_id
                   WHERE jobs.job_id = ? AND jobs.owner_id = ?""",
                (job_id, owner_id),
            ).fetchone()
            return _decode_job(row)
        finally:
            connection.close()

    def list_recent_jobs(self, owner_id: str, *, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent public jobs for browser refresh recovery and global progress."""
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                """SELECT jobs.*, documents.title AS document_title, documents.original_name AS document_name
                   FROM knowledge_ingestion_jobs AS jobs
                   LEFT JOIN user_documents AS documents ON documents.doc_id = jobs.document_id AND documents.user_id = jobs.owner_id
                   WHERE jobs.owner_id = ? ORDER BY jobs.updated_at DESC LIMIT ?""",
                (owner_id, max(1, min(int(limit), 100))),
            ).fetchall()
            return [job for row in rows if (job := _decode_job(row)) is not None]
        finally:
            connection.close()

    def latest_ingestion(self, *, document_id: str, owner_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest public lifecycle snapshot for one owned document."""
        connection = self._connection_factory()
        try:
            row = connection.execute(
                """SELECT jobs.*, documents.title AS document_title, documents.original_name AS document_name
                   FROM knowledge_ingestion_jobs AS jobs
                   LEFT JOIN user_documents AS documents ON documents.doc_id = jobs.document_id AND documents.user_id = jobs.owner_id
                   WHERE jobs.document_id = ? AND jobs.owner_id = ?
                   ORDER BY jobs.created_at DESC LIMIT 1""",
                (document_id, owner_id),
            ).fetchone()
            return _decode_job(row)
        finally:
            connection.close()

    def recover_interrupted_jobs(self) -> int:
        """Requeue abandoned work and honour durable cancellations during startup.

        Inputs:
            None. The prior process may have exited while holding leases.
        Outputs:
            Number of persisted rows transitioned to a recoverable terminal or queued state.
        Called by:
            Application lifespan before the knowledge worker starts.
        Side effects:
            Clears stale leases. No partial source result is fabricated.
        Failure:
            Rolls back every recovery write if SQLite rejects the transition.
        Invariants:
            A cancel request always wins over restart recovery.
        """
        connection, now = self._connection_factory(), _now()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cancelled = connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET status = 'cancelled', stage = 'cancelled', progress = 100,
                       completed_at = ?, worker_id = NULL, lease_token = NULL,
                       lease_expires_at = NULL, heartbeat_at = NULL, updated_at = ?
                   WHERE status IN ('processing', 'cancelling') AND cancel_requested = 1""",
                (now, now),
            ).rowcount
            requeued = connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET status = 'queued', stage = 'queued', progress = 0,
                       worker_id = NULL, lease_token = NULL, lease_expires_at = NULL,
                       heartbeat_at = NULL, updated_at = ?
                   WHERE status = 'processing' AND cancel_requested = 0""",
                (now,),
            ).rowcount
            connection.commit()
            return int(cancelled or 0) + int(requeued or 0)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def claim_next(self, worker_id: str, *, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> Optional[Dict[str, Any]]:
        """Atomically lease the next queued job and return a worker-only snapshot."""
        connection, now = self._connection_factory(), _now()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET status = 'cancelled', stage = 'cancelled', progress = 100,
                       completed_at = ?, worker_id = NULL, lease_token = NULL,
                       lease_expires_at = NULL, heartbeat_at = NULL, updated_at = ?
                   WHERE status IN ('processing', 'cancelling') AND cancel_requested = 1
                     AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?""",
                (now, now, now),
            )
            connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET status = 'queued', stage = 'queued', progress = 0,
                       worker_id = NULL, lease_token = NULL, lease_expires_at = NULL,
                       heartbeat_at = NULL, updated_at = ?
                   WHERE status = 'processing' AND cancel_requested = 0
                     AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?""",
                (now, now),
            )
            row = connection.execute(
                """SELECT job_id FROM knowledge_ingestion_jobs
                   WHERE status = 'queued' AND cancel_requested = 0
                   ORDER BY created_at ASC LIMIT 1"""
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            job_id, lease_token = str(row["job_id"]), str(uuid.uuid4())
            changed = connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET status = 'processing', stage = 'preparing', progress = CASE WHEN progress < 1 THEN 1 ELSE progress END,
                       attempt_count = attempt_count + 1, worker_id = ?, lease_token = ?,
                       lease_expires_at = ?, heartbeat_at = ?, updated_at = ?
                   WHERE job_id = ? AND status = 'queued' AND cancel_requested = 0""",
                (worker_id, lease_token, _expiry(lease_seconds), now, now, job_id),
            )
            if changed.rowcount != 1:
                connection.rollback()
                return None
            snapshot = _decode_job(
                connection.execute("SELECT * FROM knowledge_ingestion_jobs WHERE job_id = ?", (job_id,)).fetchone(),
                include_lease=True,
            )
            connection.commit()
            return snapshot
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def heartbeat(self, job_id: str, worker_id: str, lease_token: str, *, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> bool:
        """Renew one active worker lease without exposing it through public reads."""
        connection = self._connection_factory()
        try:
            changed = connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET heartbeat_at = ?, lease_expires_at = ?, updated_at = ?
                   WHERE job_id = ? AND status = 'processing' AND worker_id = ? AND lease_token = ?
                     AND cancel_requested = 0""",
                (_now(), _expiry(lease_seconds), _now(), job_id, worker_id, lease_token),
            )
            connection.commit()
            return changed.rowcount == 1
        finally:
            connection.close()

    def is_cancel_requested(self, job_id: str, worker_id: str, lease_token: str) -> bool:
        """Check cancellation while proving that the caller still owns the lease."""
        connection = self._connection_factory()
        try:
            row = connection.execute(
                """SELECT cancel_requested FROM knowledge_ingestion_jobs
                   WHERE job_id = ? AND worker_id = ? AND lease_token = ? AND status IN ('processing', 'cancelling')""",
                (job_id, worker_id, lease_token),
            ).fetchone()
            return row is None or bool(row["cancel_requested"])
        finally:
            connection.close()

    def update_progress(self, job_id: str, worker_id: str, lease_token: str, *, stage: str, progress: int) -> bool:
        """Publish a bounded progress checkpoint from the current worker only."""
        connection = self._connection_factory()
        try:
            changed = connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET stage = ?, progress = ?, heartbeat_at = ?, lease_expires_at = ?, updated_at = ?
                   WHERE job_id = ? AND status = 'processing' AND cancel_requested = 0
                     AND worker_id = ? AND lease_token = ?""",
                (str(stage)[:80], max(0, min(99, int(progress))), _now(), _expiry(DEFAULT_LEASE_SECONDS), _now(),
                 job_id, worker_id, lease_token),
            )
            connection.commit()
            return changed.rowcount == 1
        finally:
            connection.close()

    def complete(self, job_id: str, worker_id: str, lease_token: str, *, result: Optional[Dict[str, Any]] = None, chunk_count: Optional[int] = None, index_version: Optional[str] = None) -> bool:
        """Finalize one leased job after the parser/index adapter has completed safely."""
        connection, now = self._connection_factory(), _now()
        try:
            changed = connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET status = 'completed', stage = 'completed', progress = 100, result = ?, chunk_count = ?,
                       index_version = COALESCE(?, index_version), error_message = NULL, completed_at = ?,
                       worker_id = NULL, lease_token = NULL, lease_expires_at = NULL, heartbeat_at = NULL, updated_at = ?
                   WHERE job_id = ? AND status = 'processing' AND cancel_requested = 0
                     AND worker_id = ? AND lease_token = ?""",
                (json.dumps(result or {}, ensure_ascii=False), chunk_count, index_version, now, now,
                 job_id, worker_id, lease_token),
            )
            connection.commit()
            return changed.rowcount == 1
        finally:
            connection.close()

    def fail(self, job_id: str, worker_id: str, lease_token: str, error_message: str) -> bool:
        """Record a safe terminal failure without allowing stale workers to overwrite recovery."""
        connection, now = self._connection_factory(), _now()
        try:
            changed = connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET status = 'failed', stage = 'failed', error_message = ?, completed_at = ?,
                       worker_id = NULL, lease_token = NULL, lease_expires_at = NULL, heartbeat_at = NULL, updated_at = ?
                   WHERE job_id = ? AND status = 'processing' AND cancel_requested = 0
                     AND worker_id = ? AND lease_token = ?""",
                (str(error_message or "Knowledge preparation failed")[:1000], now, now, job_id, worker_id, lease_token),
            )
            connection.commit()
            return changed.rowcount == 1
        finally:
            connection.close()

    def cancel(self, owner_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Cancel queued work immediately or request cancellation at an active checkpoint."""
        connection, now = self._connection_factory(), _now()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM knowledge_ingestion_jobs WHERE job_id = ? AND owner_id = ?",
                (job_id, owner_id),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            if row["status"] == "queued":
                connection.execute(
                    """UPDATE knowledge_ingestion_jobs
                       SET status = 'cancelled', stage = 'cancelled', progress = 100, cancel_requested = 1,
                           completed_at = ?, updated_at = ? WHERE job_id = ? AND owner_id = ?""",
                    (now, now, job_id, owner_id),
                )
            elif row["status"] == "processing":
                connection.execute(
                    """UPDATE knowledge_ingestion_jobs
                       SET status = 'cancelling', stage = 'cancelling', cancel_requested = 1, updated_at = ?
                       WHERE job_id = ? AND owner_id = ?""",
                    (now, job_id, owner_id),
                )
            connection.commit()
            return self.get_job(owner_id, job_id)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_cancelled(self, job_id: str, worker_id: str, lease_token: str) -> bool:
        """Finalize a cooperative cancellation after the worker reaches a safe checkpoint."""
        connection, now = self._connection_factory(), _now()
        try:
            changed = connection.execute(
                """UPDATE knowledge_ingestion_jobs
                   SET status = 'cancelled', stage = 'cancelled', progress = 100, completed_at = ?,
                       worker_id = NULL, lease_token = NULL, lease_expires_at = NULL, heartbeat_at = NULL, updated_at = ?
                   WHERE job_id = ? AND status IN ('processing', 'cancelling')
                     AND worker_id = ? AND lease_token = ?""",
                (now, now, job_id, worker_id, lease_token),
            )
            connection.commit()
            return changed.rowcount == 1
        finally:
            connection.close()

    def retry(self, owner_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Create a new queued job from a terminal job's immutable source version."""
        connection, now = self._connection_factory(), _now()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT version_id, document_id, job_type, status FROM knowledge_ingestion_jobs
                   WHERE job_id = ? AND owner_id = ?""",
                (job_id, owner_id),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            if row["status"] not in _TERMINAL_STATUSES:
                connection.commit()
                return self.get_job(owner_id, job_id)
            next_job_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO knowledge_ingestion_jobs
                   (job_id, version_id, document_id, owner_id, job_type, status, stage, progress,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'queued', 'queued', 0, ?, ?)""",
                (next_job_id, row["version_id"], row["document_id"], owner_id, row["job_type"], now, now),
            )
            connection.commit()
            return self.get_job(owner_id, next_job_id)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def user_document_stats(self, user_id: str) -> Dict[str, Any]:
        """Return the stable document-space summary used by legacy endpoints."""
        connection = self._connection_factory()
        try:
            total_documents = connection.execute("SELECT COUNT(*) FROM user_documents WHERE user_id = ?", (user_id,)).fetchone()[0]
            status_rows = connection.execute(
                "SELECT parse_status, COUNT(*) AS count FROM user_documents WHERE user_id = ? GROUP BY parse_status",
                (user_id,),
            ).fetchall()
            total_size = connection.execute("SELECT COALESCE(SUM(file_size), 0) FROM user_documents WHERE user_id = ?", (user_id,)).fetchone()[0]
            status_stats = {str(row["parse_status"]): int(row["count"]) for row in status_rows}
            return {"total_documents": int(total_documents or 0), "status_stats": status_stats, "total_size": int(total_size or 0)}
        finally:
            connection.close()

    def record_retrieval(self, *, owner_id: str, question: str, mode: str, candidate_count: int, ranked_count: int, citations: Sequence[Dict[str, Any]]) -> str:
        """Store a privacy-scoped, implementation-neutral answer trace."""
        trace_id = str(uuid.uuid4())
        connection = self._connection_factory()
        try:
            connection.execute(
                """INSERT INTO knowledge_retrieval_traces
                   (trace_id, owner_id, question, mode, candidate_count, ranked_count, citations, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (trace_id, owner_id, question[:2000], mode, candidate_count, ranked_count,
                 json.dumps(list(citations), ensure_ascii=False), _now()),
            )
            connection.commit()
            return trace_id
        finally:
            connection.close()

    def record_knowledge_use(self, *, owner_id: str, mode: str, candidate_count: int, ranked_count: int, source_count: int, citation_count: int, answerable: bool) -> str:
        """Record only aggregate retrieval outcome for opt-in profile analysis."""
        event_id = str(uuid.uuid4())
        connection = self._connection_factory()
        try:
            connection.execute(
                """INSERT INTO knowledge_use_events
                   (event_id, owner_id, mode, candidate_count, ranked_count, source_count,
                    citation_count, answerable, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, owner_id, str(mode or "hybrid")[:80], max(0, int(candidate_count)),
                 max(0, int(ranked_count)), max(0, int(source_count)), max(0, int(citation_count)),
                 1 if answerable else 0, _now()),
            )
            connection.commit()
            return event_id
        finally:
            connection.close()

    def summarize_profile_knowledge_use(self, owner_id: str) -> Dict[str, Any]:
        """Return owner-scoped aggregates without queries, source ids, or citations."""
        connection = self._connection_factory()
        try:
            row = connection.execute(
                """SELECT COUNT(*) AS knowledge_use_count,
                          COALESCE(SUM(CASE WHEN answerable = 1 THEN 1 ELSE 0 END), 0) AS answerable_use_count,
                          COALESCE(SUM(CASE WHEN citation_count > 0 THEN 1 ELSE 0 END), 0) AS cited_use_count,
                          COALESCE(SUM(CASE WHEN answerable = 1 AND source_count > 0 AND citation_count > 0 THEN 1 ELSE 0 END), 0) AS reliable_use_count,
                          MIN(CASE WHEN answerable = 1 AND source_count > 0 AND citation_count > 0 THEN created_at END) AS observed_from,
                          MAX(CASE WHEN answerable = 1 AND source_count > 0 AND citation_count > 0 THEN created_at END) AS observed_to
                   FROM knowledge_use_events WHERE owner_id = ?""",
                (owner_id,),
            ).fetchone()
            return {"knowledge_use_count": int(row["knowledge_use_count"] or 0), "answerable_use_count": int(row["answerable_use_count"] or 0), "cited_use_count": int(row["cited_use_count"] or 0), "reliable_use_count": int(row["reliable_use_count"] or 0), "observation_range": {"observed_from": row["observed_from"], "observed_to": row["observed_to"]}}
        finally:
            connection.close()

    def list_retrievals(self, *, owner_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """List owner-scoped recent answer traces for the workspace activity view."""
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                """SELECT trace_id, question, mode, candidate_count, ranked_count, citations, created_at
                   FROM knowledge_retrieval_traces WHERE owner_id = ? ORDER BY created_at DESC LIMIT ?""",
                (owner_id, max(1, min(limit, 100))),
            ).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["citations"] = _decode_json(item.get("citations"), [])
                results.append(item)
            return results
        finally:
            connection.close()
