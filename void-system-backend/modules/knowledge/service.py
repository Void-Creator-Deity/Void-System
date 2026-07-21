"""Application composition for the unified Knowledge Engine."""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Mapping, Optional

from adapters.chroma.knowledge_store import ChromaKnowledgeStore
from adapters.sqlite.knowledge_lifecycle_repository import SQLiteKnowledgeLifecycleRepository
from adapters.sqlite.knowledge_document_repository import SQLiteKnowledgeDocumentRepository
from adapters.sqlite.user_knowledge_repository import SQLiteUserKnowledgeRepository
from core.knowledge_contracts import KnowledgeQuery, KnowledgeScope
from core.runtime_settings import RuntimeSettings
from database import Database
from modules.knowledge.generator import LangChainGroundedGenerator
from modules.knowledge.encrypted_storage import KnowledgeSourceCipher
from modules.knowledge.indexes import ScopedLexicalIndex, ScopedSemanticIndex
from modules.knowledge.ingestion import PersonalKnowledgeIngestor
from modules.knowledge.personal_documents import PersonalKnowledgeDocumentManager
from modules.knowledge.responders import GroundedKnowledgeResponder
from modules.knowledge.retrieval import EvidenceReranker, ReciprocalRankFusionIndex
from modules.knowledge.shared_documents import SharedKnowledgeDocumentManager
from modules.knowledge.workspace import KnowledgeWorkspace
from modules.knowledge.engine import KnowledgeEngine


class DeferredKnowledgeMaintenance:
    """Create retrieval infrastructure only when a workspace maintenance action needs it.

    Listing, editing, archiving, and restoring document metadata do not require
    an embedding provider. Rebuild, purge, and index diagnostics resolve the
    same PersonalKnowledgeDocumentManager used by the normal ingestion path.
    """

    def __init__(self, factory: Any) -> None:
        self._factory = factory
        self._delegate: Any = None
        self._lock = Lock()

    def _get(self) -> Any:
        if self._delegate is None:
            with self._lock:
                if self._delegate is None:
                    self._delegate = self._factory()
        return self._delegate

    def enqueue_rebuild_jobs(self, owner_id: str) -> Dict[str, Any]:
        return self._get().enqueue_rebuild_jobs(owner_id)

    def index_stats(self, owner_id: str) -> Dict[str, Any]:
        return self._get().index_stats(owner_id)

    def delete_indexed_document(self, owner_id: str, document_id: str) -> bool:
        return self._get().delete_indexed_document(owner_id, document_id)


@dataclass(frozen=True)
class UserKnowledgeResources:
    """All application-owned modules needed by personal knowledge HTTP routes."""

    engine: KnowledgeEngine
    workspace: KnowledgeWorkspace
    lifecycle_repository: SQLiteKnowledgeLifecycleRepository
    document_manager: PersonalKnowledgeDocumentManager


@dataclass(frozen=True)
class SystemKnowledgeResources:
    """All application-owned modules needed by shared knowledge HTTP routes."""

    engine: KnowledgeEngine
    manager: SharedKnowledgeDocumentManager


def _knowledge_cipher(settings: RuntimeSettings) -> KnowledgeSourceCipher:
    """Resolve the single application key used for private source, preview, and index content."""
    return KnowledgeSourceCipher(settings, settings.BASE_DIR / "user_documents")


def _shared_manager(database: Database, store: ChromaKnowledgeStore, catalog: Optional[SQLiteKnowledgeDocumentRepository] = None) -> SharedKnowledgeDocumentManager:
    manager = SharedKnowledgeDocumentManager(database=database, store=store, document_repository=catalog)
    store.migrate_legacy_shared_collection(manager.active_catalog())
    return manager


def _catalog_resolver(catalog: SQLiteKnowledgeDocumentRepository):
    """Resolve private and shared eligibility from one authoritative library catalogue.

    Inputs: the query and retrieval scope. Outputs: only document records that
    the owner may search. Called by both lexical and semantic indexes. The user
    scope returns owned uploads; the shared scope returns joined catalogue items
    unless the caller deliberately sets include_global_shared.
    """
    def resolve(query: KnowledgeQuery, scope: KnowledgeScope) -> Mapping[str, Mapping[str, object]]:
        if not query.owner_id:
            return {}
        filters = query.filters if isinstance(query.filters, dict) else {}
        tags = [str(tag).strip() for tag in filters.get("tags", []) if str(tag).strip()]
        include_global_shared = bool(filters.get("include_global_shared", False))
        full_catalog = catalog.active_library_catalog(
            owner_id=query.owner_id,
            tags=tags or None,
            document_ids=query.document_ids,
            include_global_shared=include_global_shared,
        )
        if scope == KnowledgeScope.USER:
            return {
                document_id: document
                for document_id, document in full_catalog.items()
                if document.get("visibility") == SQLiteKnowledgeDocumentRepository.PRIVATE
            }
        if scope == KnowledgeScope.SYSTEM:
            return {
                document_id: document
                for document_id, document in full_catalog.items()
                if document.get("visibility") == SQLiteKnowledgeDocumentRepository.OFFICIAL
            }
        return {}
    return resolve


def _shared_catalog_resolver(shared_manager: SharedKnowledgeDocumentManager):
    """Resolve the global shared catalogue for administrator-only maintenance tools."""
    def resolve(query: KnowledgeQuery, scope: KnowledgeScope) -> Mapping[str, Mapping[str, object]]:
        if scope != KnowledgeScope.SYSTEM:
            return {}
        filters = query.filters if isinstance(query.filters, dict) else {}
        tags = [str(tag).strip() for tag in filters.get("tags", []) if str(tag).strip()]
        return shared_manager.active_catalog(tags or None, list(query.document_ids or []))
    return resolve


def _engine(
    *,
    store: ChromaKnowledgeStore,
    catalog: Any,
    settings: Optional[RuntimeSettings],
    ingestor: Any = None,
    lifecycle_repository: Optional[SQLiteKnowledgeLifecycleRepository] = None,
) -> KnowledgeEngine:
    return KnowledgeEngine(
        index=ReciprocalRankFusionIndex([
            ScopedSemanticIndex(store, catalog),
            ScopedLexicalIndex(store, catalog),
        ]),
        reranker=EvidenceReranker(max_per_document=2),
        responder=GroundedKnowledgeResponder(LangChainGroundedGenerator(settings=settings)),
        ingestor=ingestor,
        trace_recorder=lifecycle_repository,
        use_recorder=lifecycle_repository,
    )


def migrate_private_knowledge_sources(database: Database, settings: RuntimeSettings) -> Dict[str, Any]:
    """Apply private preview and source-storage protection before workers resume.

    Inputs: the runtime database and encryption settings. Outputs: explicit
    preview and source-storage maintenance counts. Called by application startup.
    This intentionally avoids embedding clients; encrypted index rebuilds are
    queued separately once retrieval resources are available.
    """
    cipher = _knowledge_cipher(settings)
    catalog = SQLiteKnowledgeDocumentRepository(database.get_connection, cipher=cipher)
    manager = PersonalKnowledgeDocumentManager(
        database=database,
        store=None,  # Source migration does not touch Chroma.
        settings=settings,
        cipher=cipher,
        document_repository=catalog,
    )
    preview_migration = catalog.migrate_legacy_private_previews()
    source_migration = manager.migrate_private_source_storage()
    return {**source_migration, "preview_migrated_count": preview_migration["migrated_count"], "preview_failures": preview_migration["failed"]}


def create_user_knowledge_workspace(database: Database, settings: Optional[RuntimeSettings] = None) -> KnowledgeWorkspace:
    """Compose personal metadata workflows without loading embeddings on list views."""
    if settings is None:
        raise ValueError("Knowledge workspace requires RuntimeSettings")
    lifecycle = SQLiteKnowledgeLifecycleRepository(database.get_connection)
    cipher = _knowledge_cipher(settings)
    repository = SQLiteUserKnowledgeRepository(database.get_connection, cipher=cipher)
    catalog = SQLiteKnowledgeDocumentRepository(database.get_connection, cipher=cipher)

    def create_documents() -> PersonalKnowledgeDocumentManager:
        return PersonalKnowledgeDocumentManager(
            database=database,
            store=ChromaKnowledgeStore(settings, cipher=cipher),
            lifecycle_repository=lifecycle,
            settings=settings,
            cipher=cipher,
            document_repository=catalog,
        )

    return KnowledgeWorkspace(repository, DeferredKnowledgeMaintenance(create_documents), lifecycle)


def create_user_knowledge_resources(database: Database, settings: Optional[RuntimeSettings] = None) -> UserKnowledgeResources:
    """Compose personal ingestion and retrieval over the single Chroma adapter."""
    if settings is None:
        raise ValueError("Knowledge resources require RuntimeSettings")
    cipher = _knowledge_cipher(settings)
    store = ChromaKnowledgeStore(settings, cipher=cipher)
    lifecycle = SQLiteKnowledgeLifecycleRepository(database.get_connection)
    repository = SQLiteUserKnowledgeRepository(database.get_connection, cipher=cipher)
    catalog_repository = SQLiteKnowledgeDocumentRepository(database.get_connection, cipher=cipher)
    documents = PersonalKnowledgeDocumentManager(database=database, store=store, lifecycle_repository=lifecycle, settings=settings, cipher=cipher, document_repository=catalog_repository)
    shared = _shared_manager(database, store, catalog_repository)
    catalog = _catalog_resolver(catalog_repository)
    workspace = KnowledgeWorkspace(repository, documents, lifecycle)
    return UserKnowledgeResources(
        engine=_engine(store=store, catalog=catalog, settings=settings, ingestor=PersonalKnowledgeIngestor(documents), lifecycle_repository=lifecycle),
        workspace=workspace,
        lifecycle_repository=lifecycle,
        document_manager=documents,
    )


def create_system_knowledge_resources(database: Database, settings: Optional[RuntimeSettings] = None) -> SystemKnowledgeResources:
    """Compose shared retrieval through the same store, retrieval, and answer path."""
    if settings is None:
        raise ValueError("System knowledge resources require RuntimeSettings")
    store = ChromaKnowledgeStore(settings)
    catalog_repository = SQLiteKnowledgeDocumentRepository(database.get_connection)
    shared = _shared_manager(database, store, catalog_repository)
    return SystemKnowledgeResources(
        engine=_engine(store=store, catalog=_shared_catalog_resolver(shared), settings=settings),
        manager=shared,
    )
