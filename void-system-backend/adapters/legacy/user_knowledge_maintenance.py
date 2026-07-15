"""Legacy infrastructure adapter for personal knowledge maintenance."""
from __future__ import annotations

from threading import Lock
from typing import Any, Callable, Dict

from core.knowledge_workspace_contracts import KnowledgeMaintenance


class LegacyUserKnowledgeMaintenance(KnowledgeMaintenance):
    """Keep parser and Chroma details outside the Knowledge Workspace module."""

    def __init__(self, document_manager: Any, vector_manager: Any) -> None:
        self._document_manager = document_manager
        self._vector_manager = vector_manager

    async def rebuild_index(self, owner_id: str) -> Dict[str, Any]:
        return await self._document_manager.rebuild_user_index(owner_id)

    def index_stats(self, owner_id: str) -> Dict[str, Any]:
        return self._vector_manager.get_collection_stats(owner_id)

    def delete_indexed_document(self, owner_id: str, document_id: str) -> bool:
        return bool(self._vector_manager.delete_document_vectors(owner_id, document_id))


class DeferredUserKnowledgeMaintenance(KnowledgeMaintenance):
    """Load optional parser/vector infrastructure only for maintenance actions."""

    def __init__(self, factory: Callable[[], KnowledgeMaintenance]) -> None:
        self._factory = factory
        self._delegate: KnowledgeMaintenance | None = None
        self._lock = Lock()

    def _get_delegate(self) -> KnowledgeMaintenance:
        if self._delegate is not None:
            return self._delegate
        with self._lock:
            if self._delegate is None:
                self._delegate = self._factory()
        return self._delegate

    async def rebuild_index(self, owner_id: str) -> Dict[str, Any]:
        return await self._get_delegate().rebuild_index(owner_id)

    def index_stats(self, owner_id: str) -> Dict[str, Any]:
        return self._get_delegate().index_stats(owner_id)

    def delete_indexed_document(self, owner_id: str, document_id: str) -> bool:
        return self._get_delegate().delete_indexed_document(owner_id, document_id)
