"""Application composition for Knowledge Engine modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from adapters.legacy.knowledge_adapters import (
    build_legacy_system_knowledge_engine,
    build_legacy_user_knowledge_engine,
)
from adapters.legacy.user_knowledge_maintenance import (
    DeferredUserKnowledgeMaintenance,
    LegacyUserKnowledgeMaintenance,
)
from adapters.sqlite.knowledge_lifecycle_repository import SQLiteKnowledgeLifecycleRepository
from adapters.sqlite.user_knowledge_repository import SQLiteUserKnowledgeRepository
from database import Database
from core.runtime_settings import RuntimeSettings
from modules.knowledge.engine import KnowledgeEngine
from modules.knowledge.workspace import KnowledgeWorkspace


@dataclass(frozen=True)
class UserKnowledgeResources:
    """Application-owned product modules for personal knowledge workflows."""

    engine: KnowledgeEngine
    workspace: KnowledgeWorkspace
    lifecycle_repository: SQLiteKnowledgeLifecycleRepository


def _create_legacy_user_knowledge_managers(
    database: Database,
    settings: Optional[RuntimeSettings],
    lifecycle_repository: SQLiteKnowledgeLifecycleRepository,
) -> tuple[Any, Any]:
    """Create legacy parser/vector managers at the infrastructure boundary."""
    from api.user_document_manager import UserDocumentManager
    from api.user_vector_manager import UserVectorManager

    vector_kwargs = {"database": database}
    if settings is not None:
        vector_kwargs["settings"] = settings
    vector_manager = UserVectorManager(**vector_kwargs)
    document_kwargs = {
        "database": database,
        "vector_manager": vector_manager,
        "lifecycle_repository": lifecycle_repository,
    }
    if settings is not None:
        document_kwargs["settings"] = settings
    document_manager = UserDocumentManager(**document_kwargs)
    return document_manager, vector_manager


def create_user_knowledge_workspace(
    database: Database, settings: Optional[RuntimeSettings] = None
) -> KnowledgeWorkspace:
    """Compose metadata workflows without eagerly loading optional AI adapters."""
    lifecycle_repository = SQLiteKnowledgeLifecycleRepository(database.get_connection)
    repository = SQLiteUserKnowledgeRepository(database.get_connection)

    def create_maintenance() -> LegacyUserKnowledgeMaintenance:
        document_manager, vector_manager = _create_legacy_user_knowledge_managers(
            database, settings, lifecycle_repository
        )
        return LegacyUserKnowledgeMaintenance(document_manager, vector_manager)

    maintenance = DeferredUserKnowledgeMaintenance(create_maintenance)
    return KnowledgeWorkspace(repository, maintenance, lifecycle_repository)


def create_user_knowledge_resources(
    database: Database, settings: Optional[RuntimeSettings] = None
) -> UserKnowledgeResources:
    """Compose personal knowledge modules over focused and legacy adapters."""
    lifecycle_repository = SQLiteKnowledgeLifecycleRepository(database.get_connection)
    repository = SQLiteUserKnowledgeRepository(database.get_connection)
    document_manager, vector_manager = _create_legacy_user_knowledge_managers(
        database, settings, lifecycle_repository
    )
    maintenance = LegacyUserKnowledgeMaintenance(document_manager, vector_manager)
    workspace = KnowledgeWorkspace(repository, maintenance, lifecycle_repository)
    engine_kwargs = {"trace_recorder": lifecycle_repository}
    if settings is not None:
        engine_kwargs["settings"] = settings
    engine = build_legacy_user_knowledge_engine(
        document_manager,
        vector_manager,
        repository,
        **engine_kwargs,
    )
    return UserKnowledgeResources(
        engine=engine,
        workspace=workspace,
        lifecycle_repository=lifecycle_repository,
    )


@dataclass(frozen=True)
class SystemKnowledgeResources:
    """Application-owned engine and manager for shared system knowledge."""

    engine: KnowledgeEngine
    manager: Any


def create_system_knowledge_resources(
    manager: Any,
    settings: Optional[RuntimeSettings] = None,
) -> SystemKnowledgeResources:
    """Compose system retrieval through the same engine contracts as user knowledge."""
    return SystemKnowledgeResources(
        engine=build_legacy_system_knowledge_engine(manager, settings=settings),
        manager=manager,
    )
