"""Portable contracts for permissioned personal context and long-term memory."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Protocol, Sequence


class PersonalContextError(Exception):
    """Domain error raised by the Personal Context module."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class PersonalContextRepository(Protocol):
    """Persistence interface owned by Personal Context."""

    def get_settings(self, owner_id: str) -> Optional[Dict[str, Any]]: ...

    def upsert_settings(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def create_memory(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def list_memories(
        self,
        owner_id: str,
        *,
        memory_type: Optional[str] = None,
        status: Optional[str] = None,
        review_status: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[Dict[str, Any]]: ...

    def get_memory(self, owner_id: str, memory_id: str) -> Optional[Dict[str, Any]]: ...

    def find_memory_by_source(
        self, owner_id: str, source_type: str, source_ref: str
    ) -> Optional[Dict[str, Any]]: ...

    def update_memory(
        self, owner_id: str, memory_id: str, values: Mapping[str, Any]
    ) -> bool: ...

    def delete_memory(self, owner_id: str, memory_id: str) -> bool: ...

    def create_signal(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def upsert_signal(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def list_signals(
        self, owner_id: str, *, status: Optional[str] = None, limit: int = 100
    ) -> Sequence[Dict[str, Any]]: ...

    def upsert_pattern(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def list_patterns(
        self, owner_id: str, *, status: Optional[str] = None, limit: int = 100
    ) -> Sequence[Dict[str, Any]]: ...

    def create_hypothesis(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def list_hypotheses(
        self, owner_id: str, *, status: Optional[str] = None, limit: int = 200
    ) -> Sequence[Dict[str, Any]]: ...

    def get_hypothesis(
        self, owner_id: str, hypothesis_id: str
    ) -> Optional[Dict[str, Any]]: ...

    def get_hypothesis_by_key(
        self, owner_id: str, domain: str, profile_key: str
    ) -> Optional[Dict[str, Any]]: ...

    def update_hypothesis(
        self, owner_id: str, hypothesis_id: str, values: Mapping[str, Any]
    ) -> bool: ...

    def upsert_facet(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def list_facets(
        self, owner_id: str, *, status: Optional[str] = None, limit: int = 200
    ) -> Sequence[Dict[str, Any]]: ...

    def create_feedback(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def upsert_suppression(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def get_suppression(
        self, owner_id: str, domain: str, profile_key: str
    ) -> Optional[Dict[str, Any]]: ...

    def archive_suppression(self, owner_id: str, domain: str, profile_key: str) -> bool: ...

    def record_access(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]: ...

    def list_access_log(
        self, owner_id: str, limit: int = 50
    ) -> Sequence[Dict[str, Any]]: ...


class TaskContextSource(Protocol):
    """Task Execution reads consumed by Personal Context."""

    def list_goals(
        self, user_id: str, status: Optional[str] = None
    ) -> Sequence[Dict[str, Any]]: ...

    def list_runs(
        self,
        user_id: str,
        *,
        goal_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Sequence[Dict[str, Any]]: ...


class TaskBehaviorInsightSource(Protocol):
    """Aggregate task-history signals safe for explainable profile suggestions."""

    def summarize_profile_behavior(self, user_id: str) -> Dict[str, Any]: ...


class KnowledgeBehaviorInsightSource(Protocol):
    """Aggregate personal knowledge-use outcomes safe for profile suggestions."""

    def summarize_profile_knowledge_use(self, owner_id: str) -> Dict[str, Any]: ...


class GrowthContextSource(Protocol):
    """Growth reads consumed by Personal Context."""

    def balance(self, user_id: str) -> int: ...

    def list_capabilities(self, user_id: str) -> Sequence[Dict[str, Any]]: ...


class KnowledgeContextSource(Protocol):
    """Knowledge Workspace reads consumed by Personal Context."""

    def list_documents(
        self,
        owner_id: str,
        *,
        status: Optional[str] = None,
        retention: str = "active",
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]: ...
