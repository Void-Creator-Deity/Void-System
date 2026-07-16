"""SQLite Adapter for Knowledge Engine lifecycle records."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence


class SQLiteKnowledgeLifecycleRepository:
    """Persist versioned knowledge ingestion and answer traces."""

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _decode(value: Optional[str], fallback: Any) -> Any:
        try:
            return json.loads(value) if value else fallback
        except (TypeError, json.JSONDecodeError):
            return fallback

    def start_ingestion(
        self,
        *,
        document_id: str,
        owner_id: str,
        content_fingerprint: str,
        source_size: int,
        index_version: str,
    ) -> Dict[str, Any]:
        """Create a version and queued processing job for a document upload."""
        connection = self._connection_factory()
        try:
            existing = connection.execute(
                """SELECT version_id FROM knowledge_document_versions
                   WHERE document_id = ? AND owner_id = ? AND content_fingerprint = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (document_id, owner_id, content_fingerprint),
            ).fetchone()
            if existing:
                return {"version_id": existing[0], "job_id": None, "duplicate": True}

            now = self._now()
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
                   (job_id, version_id, document_id, owner_id, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'queued', ?, ?)""",
                (job_id, version_id, document_id, owner_id, now, now),
            )
            connection.commit()
            return {"version_id": version_id, "job_id": job_id, "duplicate": False}
        finally:
            connection.close()

    def update_ingestion(
        self,
        *,
        job_id: str,
        owner_id: str,
        status: str,
        chunk_count: Optional[int] = None,
        index_version: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update lifecycle state; ownership is always part of the write."""
        fields = ["status = ?", "updated_at = ?"]
        values: List[Any] = [status, self._now()]
        if chunk_count is not None:
            fields.append("chunk_count = ?")
            values.append(chunk_count)
        if index_version is not None:
            fields.append("index_version = ?")
            values.append(index_version)
        if error_message is not None:
            fields.append("error_message = ?")
            values.append(error_message[:1000])
        if status in {"completed", "failed"}:
            fields.append("completed_at = ?")
            values.append(self._now())
        values.extend([job_id, owner_id])

        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                f"UPDATE knowledge_ingestion_jobs SET {', '.join(fields)} WHERE job_id = ? AND owner_id = ?",
                values,
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def user_document_stats(self, user_id: str) -> Dict[str, Any]:
        """Return the stable document-space summary used by legacy endpoints."""
        connection = self._connection_factory()
        try:
            total_documents = connection.execute(
                "SELECT COUNT(*) FROM user_documents WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            status_rows = connection.execute(
                """SELECT parse_status, COUNT(*) AS count FROM user_documents
                   WHERE user_id = ? GROUP BY parse_status""",
                (user_id,),
            ).fetchall()
            total_size = connection.execute(
                "SELECT COALESCE(SUM(file_size), 0) FROM user_documents WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]
            status_stats = {str(row["parse_status"]): int(row["count"]) for row in status_rows}
            return {
                "total_documents": int(total_documents or 0),
                "status_stats": status_stats,
                "total_size": int(total_size or 0),
                "completed_documents": status_stats.get("completed", 0),
            }
        finally:
            connection.close()

    def latest_ingestion(self, *, document_id: str, owner_id: str) -> Optional[Dict[str, Any]]:
        connection = self._connection_factory()
        try:
            row = connection.execute(
                """SELECT job_id, version_id, status, chunk_count, index_version, error_message,
                          created_at, updated_at, completed_at
                   FROM knowledge_ingestion_jobs
                   WHERE document_id = ? AND owner_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (document_id, owner_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def record_retrieval(
        self,
        *,
        owner_id: str,
        question: str,
        mode: str,
        candidate_count: int,
        ranked_count: int,
        citations: Sequence[Dict[str, Any]],
    ) -> str:
        """Store a privacy-scoped, implementation-neutral answer trace."""
        trace_id = str(uuid.uuid4())
        connection = self._connection_factory()
        try:
            connection.execute(
                """INSERT INTO knowledge_retrieval_traces
                   (trace_id, owner_id, question, mode, candidate_count, ranked_count, citations, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trace_id, owner_id, question[:2000], mode, candidate_count, ranked_count,
                    json.dumps(list(citations), ensure_ascii=False), self._now(),
                ),
            )
            connection.commit()
            return trace_id
        finally:
            connection.close()

    def record_knowledge_use(
        self,
        *,
        owner_id: str,
        mode: str,
        candidate_count: int,
        ranked_count: int,
        source_count: int,
        citation_count: int,
        answerable: bool,
    ) -> str:
        """Record only aggregate retrieval outcome for opt-in profile analysis."""
        event_id = str(uuid.uuid4())
        connection = self._connection_factory()
        try:
            connection.execute(
                """INSERT INTO knowledge_use_events
                   (event_id, owner_id, mode, candidate_count, ranked_count, source_count,
                    citation_count, answerable, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id,
                    owner_id,
                    str(mode or "hybrid")[:80],
                    max(0, int(candidate_count)),
                    max(0, int(ranked_count)),
                    max(0, int(source_count)),
                    max(0, int(citation_count)),
                    1 if answerable else 0,
                    self._now(),
                ),
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
                          COALESCE(SUM(CASE WHEN answerable = 1 THEN 1 ELSE 0 END), 0)
                              AS answerable_use_count,
                          COALESCE(SUM(CASE WHEN citation_count > 0 THEN 1 ELSE 0 END), 0)
                              AS cited_use_count,
                          COALESCE(SUM(CASE
                              WHEN answerable = 1 AND source_count > 0 AND citation_count > 0
                              THEN 1 ELSE 0 END), 0) AS reliable_use_count,
                          MIN(CASE
                              WHEN answerable = 1 AND source_count > 0 AND citation_count > 0
                              THEN created_at END) AS observed_from,
                          MAX(CASE
                              WHEN answerable = 1 AND source_count > 0 AND citation_count > 0
                              THEN created_at END) AS observed_to
                   FROM knowledge_use_events
                   WHERE owner_id = ?""",
                (owner_id,),
            ).fetchone()
            return {
                "knowledge_use_count": int(row["knowledge_use_count"] or 0),
                "answerable_use_count": int(row["answerable_use_count"] or 0),
                "cited_use_count": int(row["cited_use_count"] or 0),
                "reliable_use_count": int(row["reliable_use_count"] or 0),
                "observation_range": {
                    "observed_from": row["observed_from"],
                    "observed_to": row["observed_to"],
                },
            }
        finally:
            connection.close()

    def list_retrievals(self, *, owner_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                """SELECT trace_id, question, mode, candidate_count, ranked_count, citations, created_at
                   FROM knowledge_retrieval_traces
                   WHERE owner_id = ? ORDER BY created_at DESC LIMIT ?""",
                (owner_id, max(1, min(limit, 100))),
            ).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["citations"] = self._decode(item.get("citations"), [])
                results.append(item)
            return results
        finally:
            connection.close()
