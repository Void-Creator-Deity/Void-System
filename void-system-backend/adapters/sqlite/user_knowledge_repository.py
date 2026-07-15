"""Focused SQLite adapter for personal knowledge document metadata."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence

from core.knowledge_workspace_contracts import UserKnowledgeRepository

ConnectionFactory = Callable[[], sqlite3.Connection]


class SQLiteUserKnowledgeRepository(UserKnowledgeRepository):
    """Own personal knowledge metadata without exposing the legacy Database facade."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _decode(row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        for field in ("tags", "chroma_ids"):
            try:
                item[field] = json.loads(item.get(field) or "[]")
            except (TypeError, json.JSONDecodeError):
                item[field] = []
        item["is_archived"] = not bool(item.pop("is_active", 1))
        return item

    @staticmethod
    def _retention_clause(retention: str) -> str:
        if retention == "archived":
            return "is_active = 0"
        if retention == "all":
            return "1 = 1"
        return "is_active = 1"

    def list_documents(
        self,
        owner_id: str,
        *,
        status: Optional[str] = None,
        retention: str = "active",
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        clauses = ["user_id = ?", self._retention_clause(retention)]
        params: List[Any] = [owner_id]
        if status:
            clauses.append("parse_status = ?")
            params.append(status)
        where = " AND ".join(clauses)
        connection = self._connection_factory()
        try:
            total = int(connection.execute(
                f"SELECT COUNT(*) FROM user_documents WHERE {where}", params
            ).fetchone()[0])
            rows = connection.execute(
                f"SELECT * FROM user_documents WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
            return {
                "documents": [self._decode(row) for row in rows],
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total,
                    "has_more": offset + len(rows) < total,
                },
            }
        finally:
            connection.close()

    def get_document(
        self, owner_id: str, document_id: str, *, include_archived: bool = False
    ) -> Optional[Dict[str, Any]]:
        active_clause = "" if include_archived else " AND is_active = 1"
        connection = self._connection_factory()
        try:
            row = connection.execute(
                f"SELECT * FROM user_documents WHERE user_id = ? AND doc_id = ?{active_clause}",
                (owner_id, document_id),
            ).fetchone()
            return self._decode(row) if row is not None else None
        finally:
            connection.close()

    def update_document(
        self,
        owner_id: str,
        document_id: str,
        *,
        title: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
    ) -> bool:
        fields = ["updated_at = ?"]
        values: List[Any] = [datetime.now().isoformat()]
        if title is not None:
            fields.append("title = ?")
            values.append(title)
        if tags is not None:
            fields.append("tags = ?")
            values.append(json.dumps(list(tags), ensure_ascii=False))
        values.extend([document_id, owner_id])
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                f"UPDATE user_documents SET {', '.join(fields)} WHERE doc_id = ? AND user_id = ? AND is_active = 1",
                values,
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def set_archived(self, owner_id: str, document_id: str, archived: bool) -> bool:
        now = datetime.now().isoformat()
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                """UPDATE user_documents
                   SET is_active = ?, archived_at = ?, updated_at = ?
                   WHERE doc_id = ? AND user_id = ? AND is_active = ?""",
                (0 if archived else 1, now if archived else None, now, document_id, owner_id,
                 1 if archived else 0),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def purge_document(self, owner_id: str, document_id: str) -> bool:
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                "DELETE FROM user_documents WHERE doc_id = ? AND user_id = ? AND is_active = 0",
                (document_id, owner_id),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def active_document_ids(
        self, owner_id: str, requested_ids: Optional[Sequence[str]] = None
    ) -> Sequence[str]:
        clauses = ["user_id = ?", "is_active = 1", "parse_status = 'completed'"]
        params: List[Any] = [owner_id]
        clean_ids = [str(value) for value in requested_ids or [] if str(value)]
        if clean_ids:
            placeholders = ",".join("?" for _ in clean_ids)
            clauses.append(f"doc_id IN ({placeholders})")
            params.extend(clean_ids)
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                "SELECT doc_id FROM user_documents WHERE " + " AND ".join(clauses), params
            ).fetchall()
            return [str(row[0]) for row in rows]
        finally:
            connection.close()

    def stats(self, owner_id: str) -> Dict[str, Any]:
        connection = self._connection_factory()
        try:
            status_rows = connection.execute(
                """SELECT parse_status, COUNT(*) AS count FROM user_documents
                   WHERE user_id = ? AND is_active = 1 GROUP BY parse_status""",
                (owner_id,),
            ).fetchall()
            status_stats = {str(row["parse_status"]): int(row["count"]) for row in status_rows}
            active = connection.execute(
                """SELECT COUNT(*) AS count, COALESCE(SUM(file_size), 0) AS total_size
                   FROM user_documents WHERE user_id = ? AND is_active = 1""",
                (owner_id,),
            ).fetchone()
            archived = int(connection.execute(
                "SELECT COUNT(*) FROM user_documents WHERE user_id = ? AND is_active = 0",
                (owner_id,),
            ).fetchone()[0])
            return {
                "total_documents": int(active["count"] or 0),
                "status_stats": status_stats,
                "total_size": int(active["total_size"] or 0),
                "completed_documents": status_stats.get("completed", 0),
                "archived_documents": archived,
            }
        finally:
            connection.close()
