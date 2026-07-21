"""Portable contracts for the personal knowledge workspace."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence


class UserKnowledgeRepository(Protocol):
    """Persistence seam for user-owned knowledge document metadata."""

    def list_documents(
        self,
        owner_id: str,
        *,
        status: Optional[str] = None,
        retention: str = "active",
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Return a paginated document read model."""

    def get_document(
        self, owner_id: str, document_id: str, *, include_archived: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Return one owned document."""

    def update_document(
        self,
        owner_id: str,
        document_id: str,
        *,
        title: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
    ) -> bool:
        """Update user-editable document metadata."""

    def set_archived(self, owner_id: str, document_id: str, archived: bool) -> bool:
        """Move a document into or out of retention without deleting its source."""

    def purge_document(self, owner_id: str, document_id: str) -> bool:
        """Permanently remove an archived document record."""

    def active_document_ids(
        self, owner_id: str, requested_ids: Optional[Sequence[str]] = None
    ) -> Sequence[str]:
        """Return documents currently eligible for retrieval."""

    def stats(self, owner_id: str) -> Dict[str, Any]:
        """Return a stable workspace summary including retained documents."""


class KnowledgeMaintenance(Protocol):
    """Infrastructure operations kept behind an application-owned adapter."""

    def enqueue_rebuild_jobs(self, owner_id: str) -> Dict[str, Any]:
        """Persist rebuild work for active documents without running it in the caller."""

    def index_stats(self, owner_id: str) -> Dict[str, Any]:
        """Return compatibility diagnostics for the current index adapter."""

    def delete_indexed_document(self, owner_id: str, document_id: str) -> bool:
        """Permanently remove indexed chunks for one document."""
