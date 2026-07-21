"""Compatibility view over the canonical knowledge document catalog."""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from adapters.sqlite.knowledge_document_repository import SQLiteKnowledgeDocumentRepository
from core.knowledge_workspace_contracts import UserKnowledgeRepository
from modules.knowledge.encrypted_storage import KnowledgeSourceCipher


class SQLiteUserKnowledgeRepository(UserKnowledgeRepository):
    """Expose only the current user's private documents from the unified library."""

    def __init__(self, connection_factory, *, cipher: Optional[KnowledgeSourceCipher] = None):
        self._catalog = SQLiteKnowledgeDocumentRepository(connection_factory, cipher=cipher)

    def list_documents(self, owner_id: str, *, status: Optional[str] = None, retention: str = "active", limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        return self._catalog.list_documents(
            owner_id=owner_id, source="uploads", status=status, retention=retention, limit=limit, offset=offset,
        )

    def get_document(self, owner_id: str, document_id: str, *, include_archived: bool = False) -> Optional[Dict[str, Any]]:
        return self._catalog.get_document(
            visibility="private", document_id=document_id, owner_id=owner_id,
            include_archived=include_archived, viewer_id=owner_id,
        )

    def update_document(self, owner_id: str, document_id: str, *, title: Optional[str] = None, tags: Optional[Sequence[str]] = None) -> bool:
        return self._catalog.update_document(
            visibility="private", document_id=document_id, owner_id=owner_id, title=title, tags=tags,
        )

    def set_archived(self, owner_id: str, document_id: str, archived: bool) -> bool:
        return self._catalog.set_archived(owner_id, document_id, archived)

    def purge_document(self, owner_id: str, document_id: str) -> bool:
        return self._catalog.purge_private_document(owner_id, document_id)

    def active_document_ids(self, owner_id: str, requested_ids: Optional[Sequence[str]] = None) -> Sequence[str]:
        return self._catalog.active_document_ids(owner_id, requested_ids)

    def stats(self, owner_id: str) -> Dict[str, Any]:
        return self._catalog.stats(owner_id, source="uploads")
