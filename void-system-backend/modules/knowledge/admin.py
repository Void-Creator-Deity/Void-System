"""System knowledge catalog read-model use cases."""
from __future__ import annotations

from typing import List

from core.system_knowledge_contracts import SystemKnowledgeCatalogRepository


class SystemKnowledgeCatalog:
    def __init__(self, repository: SystemKnowledgeCatalogRepository) -> None:
        self._repository = repository

    def tags(self) -> List[str]:
        return self._repository.list_tags()
