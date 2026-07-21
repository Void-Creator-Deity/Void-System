"""Shared knowledge catalog operations backed by the unified knowledge store."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from adapters.chroma.knowledge_store import ChromaKnowledgeStore
from adapters.sqlite.knowledge_document_repository import SQLiteKnowledgeDocumentRepository
from modules.knowledge.parser import document_parser
from core.knowledge_contracts import KnowledgeScope
from database import Database

logger = logging.getLogger("void-system.shared_knowledge_documents")


class SharedKnowledgeDocumentManager:
    """Manage administrator-owned shared sources without process-local jobs.

    Inputs: Database plus ChromaKnowledgeStore. Outputs: catalog records and
    index results for the administration HTTP adapter. Called by: shared
    knowledge administration and retrieval composition. Side effects: updates
    the shared SQLite catalog and only the named system_knowledge collection.
    """

    def __init__(self, *, database: Database, store: ChromaKnowledgeStore, document_repository: Optional[SQLiteKnowledgeDocumentRepository] = None) -> None:
        self.db = database
        self._catalog = document_repository or SQLiteKnowledgeDocumentRepository(database.get_connection)
        self._store = store

    def add_document(self, *, file_data: bytes, metadata: Mapping[str, Any]) -> Dict[str, Any]:
        """Parse and index one shared source before returning a successful response."""
        doc_id = str(uuid.uuid4())
        file_name = str(metadata.get("file_name") or f"document-{doc_id}.txt")
        title = str(metadata.get("title") or file_name)
        uploaded_by = str(metadata.get("uploaded_by") or "")
        file_type = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "txt"
        try:
            self._catalog.create_document(
                visibility="official", document_id=doc_id, owner_id=uploaded_by or "system",
                title=title, file_name=file_name, file_type=file_type, file_size=len(file_data),
                encryption_version="not_stored", chroma_ids=[], tags=list(metadata.get("tags") or []),
                description=str(metadata.get("description") or ""), parse_status="processing",
            )
            parsed = document_parser.parse_file(file_data, file_name)
            if not parsed.get("success"):
                error = str(parsed.get("error") or "Document parsing failed")
                self._catalog.set_processing_state(visibility="official", document_id=doc_id, parse_status="failed", error_message=error)
                return {"success": False, "message": error, "error_code": "RAG_PARSE_FAILED", "status_code": 422}
            content = str(parsed.get("content") or "").strip()
            if not content:
                error = "No searchable content could be extracted from this source"
                self._catalog.set_processing_state(visibility="official", document_id=doc_id, parse_status="failed", error_message=error)
                return {"success": False, "message": error, "error_code": "RAG_PARSE_FAILED", "status_code": 422}
            indexed = self._store.index_text(
                scope=KnowledgeScope.SYSTEM,
                owner_id="system",
                document_id=doc_id,
                text=content,
                metadata={
                    "file_name": file_name,
                    "title": title,
                    "file_type": file_type,
                    "uploaded_by": uploaded_by,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            self._catalog.set_processing_state(visibility="official", document_id=doc_id, parse_status="completed", chroma_ids=list(indexed.chunk_ids))
            return {"success": True, "doc_id": doc_id, "message": "Knowledge document added", "chunk_count": len(indexed.chunk_ids)}
        except Exception:
            logger.exception("Shared knowledge ingestion failed for %s", file_name)
            self._catalog.set_processing_state(visibility="official", document_id=doc_id, parse_status="failed", error_message="Knowledge document processing failed")
            return {"success": False, "message": "Knowledge document could not be processed", "error_code": "RAG_UPLOAD_FAILED", "status_code": 503}

    def list_documents(self, filter_tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """List catalog-owned shared documents; retrieval eligibility remains catalog-driven."""
        try:
            documents = list(self._catalog.active_shared_catalog(filter_tags).values())
            return {"success": True, "documents": documents, "count": len(documents)}
        except Exception:
            logger.exception("Could not list shared knowledge")
            return {"success": False, "message": "Knowledge documents are temporarily unavailable", "error_code": "RAG_LIST_FAILED", "status_code": 503}

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        document = self._catalog.get_document(visibility="official", document_id=doc_id, include_archived=True)
        if document is None:
            return {"success": False, "message": "Knowledge document not found", "error_code": "RAG_DOCUMENT_NOT_FOUND", "status_code": 404}
        return {"success": True, "document": document}

    def update_document(self, doc_id: str, updates: Mapping[str, Any]) -> Dict[str, Any]:
        try:
            updated = self._catalog.update_document(
                visibility="official", document_id=doc_id, title=updates.get("title"),
                tags=updates.get("tags"), description=updates.get("description"),
                is_active=updates.get("is_active"),
            )
            if not updated:
                return {"success": False, "message": "Knowledge document not found", "error_code": "RAG_DOCUMENT_NOT_FOUND", "status_code": 404}
            return {"success": True, "message": "Knowledge document updated"}
        except Exception:
            logger.exception("Could not update shared knowledge %s", doc_id)
            return {"success": False, "message": "Knowledge document could not be updated", "error_code": "RAG_UPDATE_FAILED", "status_code": 503}

    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        document = self._catalog.get_document(visibility="official", document_id=doc_id, include_archived=True)
        if document is None:
            return {"success": False, "message": "Knowledge document not found", "error_code": "RAG_DOCUMENT_NOT_FOUND", "status_code": 404}
        if not self._store.delete_document(scope=KnowledgeScope.SYSTEM, owner_id="system", document_id=doc_id):
            return {"success": False, "message": "Knowledge index is temporarily unavailable", "error_code": "RAG_DELETE_FAILED", "status_code": 503}
        if not self._catalog.delete_official_document(doc_id):
            return {"success": False, "message": "Knowledge document could not be deleted", "error_code": "RAG_DELETE_FAILED", "status_code": 503}
        return {"success": True, "message": "Knowledge document deleted"}

    def reconcile_index(self) -> Dict[str, Any]:
        """Remove chunks not represented by an active shared catalog document."""
        try:
            active = self.active_catalog()
            deleted = self._store.reconcile_catalog(scope=KnowledgeScope.SYSTEM, owner_id="system", allowed_document_ids=list(active))
            return {"success": True, "message": "Knowledge index repaired", "deleted_ids_count": deleted}
        except Exception:
            logger.exception("Could not reconcile shared knowledge index")
            return {"success": False, "message": "Knowledge index could not be repaired", "error_code": "RAG_SYNC_FAILED", "status_code": 503}

    def active_catalog(self, tags: Optional[List[str]] = None, document_ids: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Return retrieval-eligible shared catalog rows indexed by document id."""
        return self._catalog.active_shared_catalog(tags, document_ids)
