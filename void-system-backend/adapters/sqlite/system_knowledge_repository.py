"""Compatibility view over official documents in the unified knowledge catalog."""
from __future__ import annotations

from typing import Callable, List

from adapters.sqlite.knowledge_document_repository import SQLiteKnowledgeDocumentRepository
from core.system_knowledge_contracts import SystemKnowledgeCatalogRepository


class SQLiteSystemKnowledgeRepository(SystemKnowledgeCatalogRepository):
    def __init__(self, connection_factory: Callable):
        self._catalog = SQLiteKnowledgeDocumentRepository(connection_factory)

    def list_tags(self) -> List[str]:
        return self._catalog.list_tags(owner_id="", source="shared")
