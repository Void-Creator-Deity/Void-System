"""Personal source ingestion adapter owned by Knowledge Engine composition."""
from __future__ import annotations

from typing import Any, Dict

from core.knowledge_contracts import IngestSource


class PersonalKnowledgeIngestor:
    """Translate the portable ingestion contract into a durable personal job."""

    def __init__(self, documents: Any) -> None:
        self._documents = documents

    async def ingest(self, source: IngestSource) -> Dict[str, Any]:
        return await self._documents.upload_and_process_document(
            user_id=source.owner_id,
            file_data=source.content,
            file_name=source.file_name,
            title=source.title,
            tags=list(source.tags),
        )
