"""Canonical SQLite repository for private and official knowledge documents.

The repository is the only runtime metadata path for the unified library.  It
preserves legacy document identifiers so vector chunks, ingestion jobs, and
source files remain valid during the transition away from the old catalogs.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from modules.knowledge.encrypted_storage import KnowledgeSourceCipher

ConnectionFactory = Callable[[], sqlite3.Connection]


class SQLiteKnowledgeDocumentRepository:
    """Own the canonical knowledge_documents catalog and its visibility rules.

    Inputs:
        A SQLite connection factory created by Database.get_connection.
    Outputs:
        Stable document read models with source, visibility, and can_manage fields.
    Called by:
        Knowledge ingestion, user library HTTP routes, administration, and retrieval catalog resolution.
    Side effects:
        Creates, updates, archives, and purges catalog metadata. It never mutates vector chunks.
    """

    PRIVATE = "private"
    OFFICIAL = "official"

    def __init__(self, connection_factory: ConnectionFactory, *, cipher: Optional[KnowledgeSourceCipher] = None) -> None:
        self._connection_factory = connection_factory
        self._cipher = cipher

    @staticmethod
    def _loads(value: Any, default: Any) -> Any:
        try:
            parsed = json.loads(value) if value else default
        except (TypeError, json.JSONDecodeError):
            parsed = default
        return parsed if isinstance(parsed, type(default)) else default

    def _protect_preview(self, visibility: str, content_preview: str) -> str:
        """Encrypt private extracted snippets before SQLite persistence."""
        if visibility != self.PRIVATE or not content_preview or self._cipher is None:
            return content_preview
        return "enc:" + self._cipher.VERSION + ":" + self._cipher.encrypt_text(content_preview)

    def _reveal_preview(self, visibility: str, content_preview: Any) -> str:
        """Reveal an authorized private preview only when it is current ciphertext."""
        value = str(content_preview or "")
        if visibility != self.PRIVATE:
            return value
        prefix = "enc:" + (self._cipher.VERSION if self._cipher else KnowledgeSourceCipher.VERSION) + ":"
        if not value or not value.startswith(prefix) or self._cipher is None:
            # Private plaintext is migration input, never a normal runtime read.
            # A malformed or incorrectly composed encrypted record also fails closed.
            return ""
        return self._cipher.decrypt_text(value[len(prefix):])

    def migrate_legacy_private_previews(self, *, limit: int = 500) -> Dict[str, Any]:
        """Encrypt historical private SQLite previews before ordinary reads resume.

        Inputs: private rows with a nonempty preview not protected by the active
        cipher. Outputs: migrated count and explicit failures. Called by the
        application startup migration before user-facing library routes run.
        Side effects: replaces only the matching plaintext value, so a concurrent
        document reprocess cannot be overwritten by stale migration work.
        """
        if self._cipher is None:
            raise RuntimeError("Private preview migration requires an encryption cipher")
        prefix = "enc:" + self._cipher.VERSION + ":"
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                """SELECT document_id, owner_id, content_preview FROM knowledge_documents
                   WHERE visibility = 'private' AND content_preview IS NOT NULL
                     AND content_preview != '' AND content_preview NOT LIKE ?
                   ORDER BY updated_at ASC LIMIT ?""",
                (prefix + "%", max(1, min(limit, 5000))),
            ).fetchall()
            migrated = 0
            failures: List[Dict[str, str]] = []
            for row in rows:
                document_id = str(row["document_id"] or "")
                owner_id = str(row["owner_id"] or "")
                plaintext = str(row["content_preview"] or "")
                if plaintext.startswith("enc:"):
                    failures.append({"document_id": document_id, "reason": "unsupported_preview_encryption"})
                    continue
                encrypted = self._protect_preview(self.PRIVATE, plaintext)
                cursor = connection.execute(
                    """UPDATE knowledge_documents SET content_preview = ?, updated_at = ?
                       WHERE document_id = ? AND visibility = 'private' AND owner_id = ?
                         AND content_preview = ?""",
                    (encrypted, datetime.now().isoformat(), document_id, owner_id, plaintext),
                )
                if cursor.rowcount == 1:
                    migrated += 1
            connection.commit()
            return {"migrated_count": migrated, "failed": failures}
        finally:
            connection.close()

    def _decode(self, row: sqlite3.Row, *, viewer_id: Optional[str] = None) -> Dict[str, Any]:
        item = dict(row)
        item["content_preview"] = self._reveal_preview(str(item.get("visibility") or ""), item.get("content_preview"))
        item["tags"] = self._loads(item.get("tags"), [])
        item["chroma_ids"] = self._loads(item.get("chroma_ids"), [])
        item["doc_id"] = item["document_id"]
        item["id"] = item["document_id"]
        item["user_id"] = item.get("owner_id")
        item["original_name"] = item.get("file_name")
        item["vector_collection"] = item.get("index_collection")
        is_in_library = bool(item.get("is_in_library", False))
        item["source"] = "upload" if item["visibility"] == self.PRIVATE else "shared"
        item["library_state"] = "owned" if item["visibility"] == self.PRIVATE else ("in_library" if is_in_library else "shared_available")
        item["is_in_library"] = is_in_library
        item["is_archived"] = not bool(item.get("is_active", 1))
        item["can_manage"] = item["visibility"] == self.PRIVATE and item.get("owner_id") == viewer_id
        return item

    @staticmethod
    def _clean_ids(values: Optional[Sequence[str]]) -> List[str]:
        return [str(value).strip() for value in values or [] if str(value).strip()]

    @staticmethod
    def _tags_match(serialized: Any, requested: Sequence[str]) -> bool:
        if not requested:
            return True
        try:
            values = json.loads(serialized or "[]")
        except (TypeError, json.JSONDecodeError):
            return False
        return bool(set(str(item) for item in values or []) & set(requested))

    def create_document(
        self,
        *,
        visibility: str,
        document_id: str,
        owner_id: Optional[str],
        title: str,
        file_name: str,
        file_type: str,
        file_size: int,
        storage_path: Optional[str] = None,
        encryption_version: str = "none",
        index_encryption_version: str = "none",
        parse_status: str = "pending",
        index_collection: Optional[str] = None,
        chroma_ids: Optional[Sequence[str]] = None,
        content_preview: str = "",
        tags: Optional[Sequence[str]] = None,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> None:
        if visibility not in (self.PRIVATE, self.OFFICIAL):
            raise ValueError("Unsupported knowledge visibility")
        if visibility == self.PRIVATE and not owner_id:
            raise ValueError("Private knowledge documents require an owner")
        now = datetime.now().isoformat()
        connection = self._connection_factory()
        try:
            connection.execute(
                """INSERT INTO knowledge_documents (
                       document_id, visibility, owner_id, title, file_name, file_type,
                       file_size, storage_path, encryption_version, index_encryption_version, parse_status, index_collection, chroma_ids,
                       content_preview, tags, description, is_active, created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    document_id, visibility, owner_id, title, file_name, file_type,
                    max(0, int(file_size or 0)), storage_path, encryption_version, index_encryption_version, parse_status, index_collection,
                    json.dumps(list(chroma_ids or []), ensure_ascii=False), self._protect_preview(visibility, content_preview),
                    json.dumps(list(tags or []), ensure_ascii=False), description,
                    int(bool(is_active)), now, now,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def set_processing_state(
        self,
        *,
        visibility: str,
        document_id: str,
        owner_id: Optional[str] = None,
        parse_status: str,
        chroma_ids: Optional[Sequence[str]] = None,
        content_preview: Optional[str] = None,
        index_collection: Optional[str] = None,
        error_message: Optional[str] = None,
        index_encryption_version: Optional[str] = None,
    ) -> bool:
        fields = ["parse_status = ?", "error_message = ?", "updated_at = ?"]
        values: List[Any] = [parse_status, error_message, datetime.now().isoformat()]
        if chroma_ids is not None:
            fields.append("chroma_ids = ?")
            values.append(json.dumps(list(chroma_ids), ensure_ascii=False))
        if content_preview is not None:
            fields.append("content_preview = ?")
            values.append(self._protect_preview(visibility, content_preview))
        if index_collection is not None:
            fields.append("index_collection = ?")
            values.append(index_collection)
        if index_encryption_version is not None:
            fields.append("index_encryption_version = ?")
            values.append(index_encryption_version)
        clauses = ["document_id = ?", "visibility = ?"]
        values.extend([document_id, visibility])
        if visibility == self.PRIVATE:
            clauses.append("owner_id = ?")
            values.append(owner_id)
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                f"UPDATE knowledge_documents SET {', '.join(fields)} WHERE {' AND '.join(clauses)}",
                values,
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def set_encryption_versions(
        self,
        *,
        owner_id: str,
        document_id: str,
        source_version: Optional[str] = None,
        index_version: Optional[str] = None,
        storage_path: Optional[str] = None,
    ) -> bool:
        """Persist completed private-data protection work without changing ownership.

        Inputs: a private document identity plus completed source/index protection
        versions and, when source storage moved, its canonical managed path.
        Outputs: whether exactly one owned private row was updated. Called by the
        private source-storage migration and encrypted index rebuild worker.
        """
        fields = ["updated_at = ?"]
        values: List[Any] = [datetime.now().isoformat()]
        if source_version is not None:
            fields.append("encryption_version = ?")
            values.append(source_version)
        if index_version is not None:
            fields.append("index_encryption_version = ?")
            values.append(index_version)
        if storage_path is not None:
            fields.append("storage_path = ?")
            values.append(storage_path)
        if len(fields) == 1:
            return False
        values.extend([document_id, owner_id])
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                f"UPDATE knowledge_documents SET {', '.join(fields)} "
                "WHERE document_id = ? AND visibility = 'private' AND owner_id = ?",
                values,
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def private_documents_requiring_source_storage_migration(
        self,
        *,
        source_version: str,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """List private sources that are not encrypted at their opaque managed path.

        A current encryption version alone is insufficient: old filenames expose
        user-provided metadata. This query keeps storage-path maintenance explicit
        and independent from encrypted Chroma index rebuild scheduling.
        """
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                """SELECT * FROM knowledge_documents
                   WHERE visibility = 'private'
                     AND (
                        encryption_version != ?
                        OR storage_path IS NULL
                        OR trim(storage_path) = ''
                        OR lower(storage_path) NOT LIKE '%.bin'
                     )
                   ORDER BY updated_at ASC LIMIT ?""",
                (source_version, max(1, min(limit, 5000))),
            ).fetchall()
            return [self._decode(row) for row in rows]
        finally:
            connection.close()

    def private_documents_requiring_index_encryption(
        self,
        *,
        index_version: str,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """List private records whose Chroma document bodies need encrypted rebuild."""
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                """SELECT * FROM knowledge_documents
                   WHERE visibility = 'private' AND index_encryption_version != ?
                   ORDER BY updated_at ASC LIMIT ?""",
                (index_version, max(1, min(limit, 5000))),
            ).fetchall()
            return [self._decode(row) for row in rows]
        finally:
            connection.close()

    def get_document(
        self,
        *,
        visibility: str,
        document_id: str,
        owner_id: Optional[str] = None,
        include_archived: bool = False,
        viewer_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        clauses = ["document_id = ?", "visibility = ?"]
        params: List[Any] = [document_id, visibility]
        if visibility == self.PRIVATE:
            clauses.append("owner_id = ?")
            params.append(owner_id)
        if not include_archived:
            clauses.append("is_active = 1")
        connection = self._connection_factory()
        try:
            row = connection.execute(
                "SELECT * FROM knowledge_documents WHERE " + " AND ".join(clauses), params
            ).fetchone()
            return self._decode(row, viewer_id=viewer_id) if row else None
        finally:
            connection.close()

    def list_documents(
        self,
        *,
        owner_id: str,
        source: str = "library",
        status: Optional[str] = None,
        retention: str = "active",
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List materials through one library model rather than separate products.

        Inputs: an authenticated user and a library view: library for owned
        uploads plus joined shared items, uploads for owned uploads, or shared
        for the global shared catalogue. Outputs: document cards with explicit
        library_state. Called by the library HTTP API. Side effects: none.
        """
        if source not in {"library", "uploads", "shared"}:
            raise ValueError("Unsupported library source")
        if retention == "archived" and source != "uploads":
            raise ValueError("Archived documents only exist in uploads")

        clauses: List[str] = []
        params: List[Any] = []
        if source == "uploads":
            clauses.extend(["visibility = 'private'", "owner_id = ?"])
            params.append(owner_id)
        elif source == "shared":
            clauses.append("visibility = 'official'")
        else:
            clauses.append(
                "((visibility = 'private' AND owner_id = ?) OR "
                "(visibility = 'official' AND EXISTS ("
                "SELECT 1 FROM user_library_entries entry "
                "WHERE entry.document_id = knowledge_documents.document_id AND entry.user_id = ?)))"
            )
            params.extend([owner_id, owner_id])
        if retention == "archived":
            clauses.append("is_active = 0")
        elif retention != "all":
            clauses.append("is_active = 1")
        if status:
            clauses.append("parse_status = ?")
            params.append(status)
        where = " AND ".join(clauses)
        entry_projection = (
            "EXISTS (SELECT 1 FROM user_library_entries entry "
            "WHERE entry.document_id = knowledge_documents.document_id AND entry.user_id = ?) AS is_in_library"
        )
        connection = self._connection_factory()
        try:
            total = int(connection.execute(
                f"SELECT COUNT(*) FROM knowledge_documents WHERE {where}", params
            ).fetchone()[0])
            rows = connection.execute(
                f"""SELECT knowledge_documents.*, {entry_projection}
                    FROM knowledge_documents WHERE {where}
                    ORDER BY CASE visibility WHEN 'private' THEN 0 ELSE 1 END, created_at DESC
                    LIMIT ? OFFSET ?""",
                [owner_id, *params, max(1, min(limit, 100)), max(0, offset)],
            ).fetchall()
            return {
                "documents": [self._decode(row, viewer_id=owner_id) for row in rows],
                "pagination": {
                    "limit": limit, "offset": offset, "total": total,
                    "has_more": offset + len(rows) < total,
                },
            }
        finally:
            connection.close()

    def add_shared_document_to_library(self, *, owner_id: str, document_id: str) -> bool:
        """Join one active shared material to a user's library without duplicating it.

        Inputs: a user id and a shared document id. Outputs: True when the
        relationship exists after the call. Called by the library add endpoint.
        Side effects: inserts at most one row in user_library_entries.
        """
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO user_library_entries (user_id, document_id)
                   SELECT ?, document_id FROM knowledge_documents
                   WHERE document_id = ? AND visibility = 'official' AND is_active = 1""",
                (owner_id, document_id),
            )
            if cursor.rowcount == 1:
                connection.commit()
                return True
            exists = connection.execute(
                "SELECT 1 FROM user_library_entries WHERE user_id = ? AND document_id = ?",
                (owner_id, document_id),
            ).fetchone()
            connection.commit()
            return exists is not None
        finally:
            connection.close()

    def remove_shared_document_from_library(self, *, owner_id: str, document_id: str) -> bool:
        """Remove only a user's shared-material reference, never the shared material."""
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                "DELETE FROM user_library_entries WHERE user_id = ? AND document_id = ?",
                (owner_id, document_id),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def active_library_catalog(
        self,
        *,
        owner_id: str,
        tags: Optional[Sequence[str]] = None,
        document_ids: Optional[Sequence[str]] = None,
        include_global_shared: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """Resolve materials eligible for one user's question.

        Default eligibility is owned private material plus shared material joined
        to that user's library. A deliberate global-search request additionally
        includes every active shared document. Both retrieval indexes consume this
        catalogue, so permissions cannot diverge by index type.
        """
        ids = self._clean_ids(document_ids)
        requested_tags = self._clean_ids(tags)
        shared_clause = "visibility = 'official'"
        params: List[Any] = [owner_id]
        if not include_global_shared:
            shared_clause += " AND EXISTS (SELECT 1 FROM user_library_entries entry WHERE entry.document_id = knowledge_documents.document_id AND entry.user_id = ?)"
            params.append(owner_id)
        clauses = [
            "is_active = 1",
            "parse_status = 'completed'",
            f"((visibility = 'private' AND owner_id = ?) OR ({shared_clause}))",
        ]
        if ids:
            clauses.append("document_id IN (" + ",".join("?" for _ in ids) + ")")
            params.extend(ids)
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                "SELECT * FROM knowledge_documents WHERE " + " AND ".join(clauses), params
            ).fetchall()
            return {
                item["document_id"]: item
                for row in rows
                for item in [self._decode(row, viewer_id=owner_id)]
                if self._tags_match(row["tags"], requested_tags)
            }
        finally:
            connection.close()

    def update_document(
        self,
        *,
        visibility: str,
        document_id: str,
        owner_id: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        fields = ["updated_at = ?"]
        values: List[Any] = [datetime.now().isoformat()]
        if title is not None:
            fields.append("title = ?")
            values.append(title)
        if tags is not None:
            fields.append("tags = ?")
            values.append(json.dumps(list(tags), ensure_ascii=False))
        if description is not None:
            fields.append("description = ?")
            values.append(description)
        if is_active is not None:
            fields.append("is_active = ?")
            values.append(int(bool(is_active)))
            fields.append("archived_at = ?")
            values.append(None if is_active else datetime.now().isoformat())
        clauses = ["document_id = ?", "visibility = ?"]
        values.extend([document_id, visibility])
        if visibility == self.PRIVATE:
            clauses.append("owner_id = ?")
            values.append(owner_id)
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                f"UPDATE knowledge_documents SET {', '.join(fields)} WHERE {' AND '.join(clauses)}",
                values,
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def set_archived(self, owner_id: str, document_id: str, archived: bool) -> bool:
        return self.update_document(
            visibility=self.PRIVATE, document_id=document_id, owner_id=owner_id, is_active=not archived,
        )

    def purge_private_document(self, owner_id: str, document_id: str) -> bool:
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                """DELETE FROM knowledge_documents WHERE document_id = ? AND visibility = 'private'
                   AND owner_id = ? AND is_active = 0""",
                (document_id, owner_id),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def delete_official_document(self, document_id: str) -> bool:
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                "DELETE FROM knowledge_documents WHERE document_id = ? AND visibility = 'official'",
                (document_id,),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def active_document_ids(self, owner_id: str, requested_ids: Optional[Sequence[str]] = None) -> List[str]:
        ids = self._clean_ids(requested_ids)
        clauses = ["visibility = 'private'", "owner_id = ?", "is_active = 1", "parse_status = 'completed'"]
        params: List[Any] = [owner_id]
        if ids:
            clauses.append("document_id IN (" + ",".join("?" for _ in ids) + ")")
            params.extend(ids)
        connection = self._connection_factory()
        try:
            return [str(row[0]) for row in connection.execute(
                "SELECT document_id FROM knowledge_documents WHERE " + " AND ".join(clauses), params
            ).fetchall()]
        finally:
            connection.close()

    def active_shared_catalog(
        self, tags: Optional[Sequence[str]] = None, document_ids: Optional[Sequence[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Resolve active shared catalogue records for administrator workflows."""
        ids = self._clean_ids(document_ids)
        clauses = ["visibility = 'official'", "is_active = 1", "parse_status = 'completed'"]
        params: List[Any] = []
        if ids:
            clauses.append("document_id IN (" + ",".join("?" for _ in ids) + ")")
            params.extend(ids)
        requested_tags = self._clean_ids(tags)
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                "SELECT * FROM knowledge_documents WHERE " + " AND ".join(clauses), params
            ).fetchall()
            return {
                item["document_id"]: item
                for row in rows
                for item in [self._decode(row)]
                if self._tags_match(row["tags"], requested_tags)
            }
        finally:
            connection.close()

    def list_tags(self, *, owner_id: str, source: str = "library") -> List[str]:
        """List tags visible in one selected library view."""
        if source not in {"library", "uploads", "shared"}:
            raise ValueError("Unsupported library source")
        clauses: List[str] = ["is_active = 1"]
        params: List[Any] = []
        if source == "uploads":
            clauses.extend(["visibility = 'private'", "owner_id = ?"])
            params.append(owner_id)
        elif source == "shared":
            clauses.append("visibility = 'official'")
        else:
            clauses.append(
                "((visibility = 'private' AND owner_id = ?) OR "
                "(visibility = 'official' AND EXISTS (SELECT 1 FROM user_library_entries entry "
                "WHERE entry.document_id = knowledge_documents.document_id AND entry.user_id = ?)))"
            )
            params.extend([owner_id, owner_id])
        connection = self._connection_factory()
        try:
            values = set()
            for row in connection.execute("SELECT tags FROM knowledge_documents WHERE " + " AND ".join(clauses), params):
                values.update(str(tag).strip() for tag in self._loads(row[0], []) if str(tag).strip())
            return sorted(values)
        finally:
            connection.close()

    def stats(self, owner_id: str, *, source: str = "library") -> Dict[str, Any]:
        """Summarise the same material visible in the selected library view."""
        listing = self.list_documents(owner_id=owner_id, source=source, retention="active", limit=100, offset=0)
        documents = listing["documents"]
        status_stats: Dict[str, int] = {}
        for item in documents:
            status = str(item.get("parse_status") or "pending")
            status_stats[status] = status_stats.get(status, 0) + 1
        archived = self.list_documents(owner_id=owner_id, source="uploads", retention="archived", limit=1, offset=0)["pagination"]["total"]
        return {
            "total_documents": len(documents),
            "status_stats": status_stats,
            "total_size": sum(int(item.get("file_size") or 0) for item in documents),
            "completed_documents": status_stats.get("completed", 0),
            "archived_documents": archived,
        }
