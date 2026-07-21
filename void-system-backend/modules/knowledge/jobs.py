"""Durable personal-knowledge ingestion and rebuild job orchestration."""
from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Callable, Dict, Mapping, Optional

from adapters.sqlite.knowledge_lifecycle_repository import SQLiteKnowledgeLifecycleRepository
from database import Database
from errors import VoidSystemException


logger = logging.getLogger("void-system.knowledge.jobs")


class KnowledgeJobService:
    """Own owner access and lease-bound execution for knowledge processing jobs.

    Inputs:
        repository: SQLite implementation containing the authoritative job state.
    Outputs:
        Owner-scoped public snapshots and worker-only claimed snapshots.
    Called by:
        Document HTTP routes and KnowledgeJobWorker.
    Side effects:
        Persists cancellation, retries, worker heartbeats, progress, and terminal results.
    Failure:
        Converts known processing failures into retryable terminal job records.
    Invariants:
        Browser request lifetimes never own processing, and an expired worker lease cannot
        overwrite a job that another worker has reclaimed.
    """

    def __init__(self, repository: SQLiteKnowledgeLifecycleRepository) -> None:
        self._repository = repository

    def get(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """Return one owner-scoped job or a stable not-found error."""
        job = self._repository.get_job(user_id, job_id)
        if job is None:
            raise VoidSystemException("Knowledge processing task was not found", "KNOWLEDGE_JOB_NOT_FOUND", 404)
        return job

    def list_recent(self, user_id: str, *, limit: int = 50) -> list[Dict[str, Any]]:
        """Return durable history used to recover the document library after refresh."""
        return self._repository.list_recent_jobs(user_id, limit=limit)

    def cancel(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """Persist a cancellation request and return the resulting public snapshot."""
        job = self._repository.cancel(user_id, job_id)
        if job is None:
            raise VoidSystemException("Knowledge processing task was not found", "KNOWLEDGE_JOB_NOT_FOUND", 404)
        return job

    def retry(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """Create a fresh queued job from a terminal task's immutable source version.

        Inputs:
            user_id/job_id: The authenticated owner and the historical task to retry.
        Outputs:
            A new queued public task snapshot. The original task stays unchanged for auditability.
        Called by:
            The personal knowledge retry HTTP endpoint.
        Failure:
            Raises a not-found error for another user's task and a conflict while work is active.
        """
        existing = self.get(user_id, job_id)
        if existing.get("status") not in {"completed", "failed", "cancelled"}:
            raise VoidSystemException(
                "Knowledge processing can be retried only after the current task finishes",
                "KNOWLEDGE_JOB_NOT_RETRYABLE",
                409,
            )
        job = self._repository.retry(user_id, job_id)
        if job is None:
            raise VoidSystemException("Knowledge processing task was not found", "KNOWLEDGE_JOB_NOT_FOUND", 404)
        return job

    def recover_interrupted_jobs(self) -> int:
        """Return expired work to the durable queue during application startup."""
        return self._repository.recover_interrupted_jobs()

    def claim_next_for_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Atomically lease the next queued knowledge job for an application worker."""
        return self._repository.claim_next(worker_id)

    def execute_claimed(
        self,
        job: Mapping[str, Any],
        process: Callable[[Mapping[str, Any], Callable[[str, int], bool]], Mapping[str, Any]],
    ) -> None:
        """Execute one claimed source operation and publish a lease-bound terminal state.

        Inputs:
            job: Private claimed snapshot containing the worker lease token.
            process: Application callback that parses and indexes the stored source.
        Outputs:
            None. Consumers observe the persisted terminal job snapshot.
        Called by:
            KnowledgeJobWorker after SQLite atomically assigns a job lease.
        Side effects:
            Updates progress, renews the lease, records a terminal result, or marks cancellation.
        Failure:
            Stores a user-safe error message; implementation details remain in server logs.
        """
        job_id = str(job.get("job_id") or "")
        worker_id = str(job.get("worker_id") or "")
        lease_token = str(job.get("lease_token") or "")
        if not job_id or not worker_id or not lease_token:
            logger.error("Knowledge worker received an unleased job")
            return

        def report(stage: str, progress: int) -> bool:
            if self._repository.is_cancel_requested(job_id, worker_id, lease_token):
                return False
            if not self._repository.heartbeat(job_id, worker_id, lease_token):
                return False
            return self._repository.update_progress(
                job_id,
                worker_id,
                lease_token,
                stage=stage,
                progress=progress,
            )

        try:
            result = dict(process(job, report) or {})
            if result.get("cancelled") or self._repository.is_cancel_requested(job_id, worker_id, lease_token):
                self._repository.mark_cancelled(job_id, worker_id, lease_token)
                return
            if not result.get("success"):
                self._repository.fail(
                    job_id,
                    worker_id,
                    lease_token,
                    str(result.get("error") or "Knowledge processing failed")[:1000],
                )
                return
            self._repository.heartbeat(job_id, worker_id, lease_token)
            self._repository.complete(
                job_id,
                worker_id,
                lease_token,
                result=result,
                chunk_count=int(result.get("chunk_count") or 0),
                index_version=str(result.get("index_version") or "legacy-chroma-v1"),
            )
        except VoidSystemException as exc:
            self._repository.fail(job_id, worker_id, lease_token, exc.message)
        except Exception as exc:
            logger.exception("Knowledge job failed (%s)", type(exc).__name__)
            self._repository.fail(
                job_id,
                worker_id,
                lease_token,
                "Knowledge processing is temporarily unavailable. Please retry.",
            )


class KnowledgeJobWorker:
    """Application-owned polling worker for durable personal knowledge jobs.

    Inputs:
        service: Lease-aware service with a SQLite-backed job queue.
        execute_claimed: Application callback that composes parser, index, and AI dependencies.
    Outputs:
        A controllable daemon worker that can be started, woken, and stopped with the app.
    Called by:
        FastAPI lifespan. HTTP routes only wake it after persisting work.
    Side effects:
        Claims jobs from SQLite and executes them outside HTTP request lifetimes.
    Invariants:
        There is no authoritative in-memory queue; SQLite is the only job source of truth.
    """

    def __init__(
        self,
        service: KnowledgeJobService,
        execute_claimed: Callable[[Mapping[str, Any]], None],
        *,
        poll_seconds: float = 1.0,
    ) -> None:
        self._service = service
        self._execute_claimed = execute_claimed
        self._poll_seconds = max(0.1, poll_seconds)
        self._worker_id = f"knowledge-worker-{uuid.uuid4()}"
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the single application worker during lifespan startup."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name=self._worker_id, daemon=True)
        self._thread.start()

    def wake(self) -> None:
        """Wake the polling worker after a route persists new or retried work."""
        self._wake.set()

    def stop(self, *, timeout: float = 5.0) -> None:
        """Request graceful shutdown; any remaining lease becomes recoverable on restart."""
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            job = self._service.claim_next_for_worker(self._worker_id)
            if job is None:
                self._wake.wait(self._poll_seconds)
                self._wake.clear()
                continue
            try:
                self._execute_claimed(job)
            except Exception as exc:
                logger.exception("Knowledge worker callback failed (%s)", type(exc).__name__)


def get_knowledge_job_service(database: Database) -> KnowledgeJobService:
    """Compose durable knowledge jobs over the application-owned SQLite connection factory."""
    return KnowledgeJobService(SQLiteKnowledgeLifecycleRepository(database.get_connection))
