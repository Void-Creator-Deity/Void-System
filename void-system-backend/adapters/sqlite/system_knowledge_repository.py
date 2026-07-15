"""SQLite read adapter for system knowledge catalog metadata."""
from __future__ import annotations

import json
from typing import Callable, List

from core.system_knowledge_contracts import SystemKnowledgeCatalogRepository


class SQLiteSystemKnowledgeRepository(SystemKnowledgeCatalogRepository):
    def __init__(self, connection_factory: Callable):
        self._connection_factory = connection_factory

    def list_tags(self) -> List[str]:
        connection = self._connection_factory()
        try:
            tags = set()
            rows = connection.execute(
                "SELECT tags FROM system_rag_documents WHERE is_active = 1"
            ).fetchall()
            for row in rows:
                try:
                    values = json.loads(row[0]) if row[0] else []
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(values, list):
                    tags.update(str(tag) for tag in values if str(tag).strip())
            return sorted(tags)
        finally:
            connection.close()
