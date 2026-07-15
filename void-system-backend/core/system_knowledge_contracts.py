"""Read contract for the system knowledge catalog."""
from __future__ import annotations

from typing import List, Protocol


class SystemKnowledgeCatalogRepository(Protocol):
    def list_tags(self) -> List[str]: ...
