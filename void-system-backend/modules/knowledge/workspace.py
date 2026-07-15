"""Personal Knowledge Workspace use cases and retention policy."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from core.knowledge_workspace_contracts import KnowledgeMaintenance, UserKnowledgeRepository


class KnowledgeWorkspace:
    """Deep module for document browsing, retention, and index maintenance."""

    def __init__(
        self,
        repository: UserKnowledgeRepository,
        maintenance: KnowledgeMaintenance,
        lifecycle_repository: Any,
    ) -> None:
        self._repository = repository
        self._maintenance = maintenance
        self._lifecycle_repository = lifecycle_repository

    def list_documents(
        self,
        owner_id: str,
        *,
        status: Optional[str] = None,
        retention: str = "active",
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        result = self._repository.list_documents(
            owner_id,
            status=status,
            retention=retention,
            limit=limit,
            offset=offset,
        )
        self._attach_lifecycle(result["documents"], owner_id)
        result["stats"] = self.stats(owner_id)
        return result

    def get_document(
        self, owner_id: str, document_id: str, *, include_archived: bool = False
    ) -> Optional[Dict[str, Any]]:
        document = self._repository.get_document(
            owner_id, document_id, include_archived=include_archived
        )
        if document is not None:
            self._attach_lifecycle([document], owner_id)
        return document

    def update_document(
        self,
        owner_id: str,
        document_id: str,
        *,
        title: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
    ) -> bool:
        return self._repository.update_document(
            owner_id, document_id, title=title, tags=tags
        )

    def archive_document(self, owner_id: str, document_id: str) -> bool:
        """Hide a document from the workspace and every retrieval path."""
        return self._repository.set_archived(owner_id, document_id, True)

    def restore_document(self, owner_id: str, document_id: str) -> bool:
        """Restore retained source and indexed content without reparsing it."""
        return self._repository.set_archived(owner_id, document_id, False)

    def purge_document(self, owner_id: str, document_id: str) -> Dict[str, Any]:
        """Permanently remove an already archived document and its indexed chunks."""
        document = self._repository.get_document(
            owner_id, document_id, include_archived=True
        )
        if document is None or not document.get("is_archived"):
            return {"purged": False, "reason": "not_found"}
        if not self._maintenance.delete_indexed_document(owner_id, document_id):
            return {"purged": False, "reason": "index_unavailable"}
        if not self._repository.purge_document(owner_id, document_id):
            return {"purged": False, "reason": "metadata_conflict"}

        file_deleted = False
        raw_path = document.get("storage_path")
        if raw_path:
            path = Path(str(raw_path))
            try:
                if path.is_file():
                    path.unlink()
                    file_deleted = True
            except OSError:
                file_deleted = False
        return {"purged": True, "file_deleted": file_deleted}

    def stats(self, owner_id: str) -> Dict[str, Any]:
        return self._repository.stats(owner_id)

    def recent_activity(self, owner_id: str, *, limit: int = 10) -> Sequence[Dict[str, Any]]:
        """Return a user-facing read model of recent grounded questions."""
        traces = self._lifecycle_repository.list_retrievals(
            owner_id=owner_id,
            limit=limit,
        )
        return [
            {
                "activity_id": trace["trace_id"],
                "question": trace["question"],
                "source_count": len(trace["citations"]),
                "sources": [
                    {
                        "document_id": citation.get("document_id"),
                        "title": citation.get("title") or "未命名资料",
                    }
                    for citation in trace["citations"]
                ],
                "created_at": trace["created_at"],
            }
            for trace in traces
        ]

    async def rebuild_index(self, owner_id: str) -> Dict[str, Any]:
        return await self._maintenance.rebuild_index(owner_id)

    def index_stats(self, owner_id: str) -> Dict[str, Any]:
        return self._maintenance.index_stats(owner_id)

    def _attach_lifecycle(self, documents: Sequence[Dict[str, Any]], owner_id: str) -> None:
        for document in documents:
            document_id = str(document.get("doc_id") or "")
            if document_id:
                document["ingestion"] = self._lifecycle_repository.latest_ingestion(
                    document_id=document_id, owner_id=owner_id
                )
