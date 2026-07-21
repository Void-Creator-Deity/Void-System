"""Personal knowledge source storage and durable ingestion execution.

The module owns user source files and SQLite metadata. Indexed chunks are always
written through ChromaKnowledgeStore; no personal code has a second vector
manager or collection policy.
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional
import uuid

from adapters.chroma.knowledge_store import ChromaKnowledgeStore
from adapters.sqlite.knowledge_document_repository import SQLiteKnowledgeDocumentRepository
from modules.knowledge.encrypted_storage import KnowledgeSourceCipher
from modules.knowledge.parser import document_parser
from core.knowledge_contracts import KnowledgeScope
from core.runtime_settings import RuntimeSettings
from database import Database

logger = logging.getLogger("void-system.personal_knowledge_documents")
ImageKnowledgeDescriber = Callable[[bytes, str], Awaitable[str]]


def _storage_safe_file_name(file_name: str) -> str:
    """Normalize an upload file name before it becomes part of a managed path."""
    raw_name = str(file_name or "").replace("\\", "/")
    candidate = raw_name.rsplit("/", 1)[-1].strip().replace("\x00", "")
    cleaned = "".join("_" if ord(char) < 32 or char in '<>:"/\\|?*' else char for char in candidate).strip(". ")
    if not cleaned:
        cleaned = "upload"
    suffix = Path(cleaned).suffix[:20]
    stem = Path(cleaned).stem or "upload"
    return f"{stem[:max(1, 180 - len(suffix))]}{suffix}"


class PersonalKnowledgeDocumentManager:
    """Persist personal sources and execute one leased ingestion job.

    Inputs: Database, ChromaKnowledgeStore, optional lifecycle repository and
    image describer. Outputs: user-facing source records and job results.
    Called by: Knowledge Engine ingestion, workspace maintenance, and durable
    job workers. Side effects: writes managed files, metadata, lifecycle rows,
    and scoped index chunks. HTTP handlers never process documents directly.
    """

    def __init__(self, *, database: Database, store: ChromaKnowledgeStore, lifecycle_repository: Any = None, settings: Any = None, storage_path: Optional[str] = None, image_describer: Optional[ImageKnowledgeDescriber] = None, cipher: Optional[KnowledgeSourceCipher] = None, document_repository: Optional[SQLiteKnowledgeDocumentRepository] = None) -> None:
        self.db = database
        self._store = store
        self._lifecycle_repository = lifecycle_repository
        # Private sources are never allowed to silently fall back to plaintext.
        # Application composition normally injects its immutable snapshot; direct
        # maintenance and test construction resolves that same canonical source.
        self._settings = settings or RuntimeSettings.from_environment()
        self._image_describer = image_describer
        self.storage_path = Path(storage_path) if storage_path else Path(__file__).resolve().parents[2] / "user_documents"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._cipher = cipher or KnowledgeSourceCipher(self._settings, self.storage_path)
        # Direct module construction is used by maintenance and tests as well as
        # the application composition root. Its local catalog must therefore use
        # the same cipher instead of silently persisting private previews in cleartext.
        self._catalog = document_repository or (
            SQLiteKnowledgeDocumentRepository(database.get_connection, cipher=self._cipher)
            if hasattr(database, "get_connection")
            else None
        )
        self.max_file_size = 50 * 1024 * 1024
        self.preview_length = 500

    async def upload_and_process_document(self, user_id: str, file_data: bytes, file_name: str, title: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Store a source and persist its durable ingestion job without indexing inline."""
        validation = self._validate_file(file_data, file_name)
        if not validation["valid"]:
            return {"success": False, "message": validation["message"], "error_code": "FILE_VALIDATION_FAILED"}
        try:
            metadata = document_parser.extract_metadata(file_data, file_name)
            doc_id = self._save_document_file(user_id, file_data, file_name)
            storage_path = self._storage_path(user_id, doc_id, file_name)
            self._create_private_document(
                user_id=user_id, doc_id=doc_id, title=title or self._generate_title(file_name, metadata),
                file_name=file_name, file_type=metadata.get("file_type", "unknown"),
                file_size=len(file_data), storage_path=str(storage_path), tags=tags or [],
            )
            self._set_private_status(user_id, doc_id, "processing", chroma_ids=[])
            lifecycle = self._start_ingestion(user_id, doc_id, file_data)
            if not lifecycle.get("job_id"):
                self._set_private_status(user_id, doc_id, "failed", error_message="Could not create the document processing task")
                return {"success": False, "message": "The document was stored but its processing task could not be created", "error_code": "KNOWLEDGE_JOB_CREATE_FAILED", "doc_id": doc_id}
            return {"success": True, "message": "Document added and processing has been queued", "doc_id": doc_id, "job_id": lifecycle["job_id"], "ingestion": lifecycle, "status": "queued"}
        except Exception:
            logger.exception("Knowledge document upload failed")
            return {"success": False, "message": "The document could not be added", "error_code": "UPLOAD_FAILED"}

    async def process_stored_document(self, user_id: str, doc_id: str, *, report_progress: Optional[Callable[[str, int], bool]] = None) -> Dict[str, Any]:
        """Parse and replace one stored source under an already claimed durable job."""
        checkpoint = lambda stage, progress: True if report_progress is None else bool(report_progress(stage, progress))
        document = self._get_private_document(user_id, doc_id)
        if document is None:
            return {"success": False, "error": "The source document no longer exists"}
        file_name = str(document.get("original_name") or "")
        storage_path = self._record_storage_path(document)
        if not file_name or not storage_path.is_file():
            return self._failed(user_id, doc_id, "The original source file is unavailable for processing")
        if not checkpoint("reading_source", 15):
            return self._cancelled(user_id, doc_id)
        try:
            file_data = self._read_source_bytes(document, storage_path)
            validation = self._validate_file(file_data, file_name)
            if not validation["valid"]:
                return self._failed(user_id, doc_id, validation["message"])
            if not checkpoint("extracting_content", 35):
                return self._cancelled(user_id, doc_id)
            parse_result = document_parser.parse_file(file_data, file_name)
            if not parse_result.get("success"):
                return self._failed(user_id, doc_id, str(parse_result.get("error") or "Document parsing failed"))
            if parse_result.get("requires_vision_enrichment"):
                if not checkpoint("understanding_image", 50):
                    return self._cancelled(user_id, doc_id)
                parse_result = await self._enrich_image(file_data, file_name, parse_result)
                if not parse_result.get("success"):
                    return self._failed(user_id, doc_id, str(parse_result.get("error") or "Image understanding failed"))
            content = str(parse_result.get("content") or "")
            if not content.strip():
                return self._failed(user_id, doc_id, "No searchable content could be extracted from this source")
            preview = content[:self.preview_length] + ("..." if len(content) > self.preview_length else "")
            self._set_private_status(user_id, doc_id, "parsed", content_preview=preview)
            if not checkpoint("building_search_index", 70):
                return self._cancelled(user_id, doc_id)
            indexed = self._store.index_text(
                scope=KnowledgeScope.USER,
                owner_id=user_id,
                document_id=doc_id,
                text=content,
                metadata={
                    "file_name": file_name,
                    "title": str((self._get_private_document(user_id, doc_id) or {}).get("title") or file_name),
                    "created_at": datetime.now().isoformat(),
                    "file_type": file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "unknown",
                },
            )
            if not checkpoint("finalizing", 95):
                self._store.delete_document(scope=KnowledgeScope.USER, owner_id=user_id, document_id=doc_id)
                return self._cancelled(user_id, doc_id)
            self._set_private_status(
                user_id, doc_id, "completed", vector_collection=indexed.collection, chroma_ids=list(indexed.chunk_ids),
                index_encryption_version=self._cipher.VERSION if self._cipher else "none",
            )
            return {"success": True, "chunk_count": len(indexed.chunk_ids), "index_version": "knowledge-store-v1", "document_id": doc_id}
        except Exception:
            logger.exception("Knowledge document processing failed for %s", doc_id)
            return self._failed(user_id, doc_id, "Document processing failed")

    def enqueue_rebuild_jobs(self, user_id: str) -> Dict[str, Any]:
        """Create durable reindex work for every active source belonging to one user."""
        try:
            documents = self._list_private_documents(user_id)
        except Exception:
            logger.exception("Could not list documents for knowledge rebuild")
            return {"success": False, "message": "Unable to load documents for rebuild", "error_code": "DOCUMENT_LIST_FAILED", "jobs": []}
        jobs: List[Dict[str, Any]] = []
        failures: List[Dict[str, str]] = []
        for document in documents:
            doc_id = str(document.get("doc_id") or "")
            storage_path = self._record_storage_path(document)
            if not doc_id or not storage_path.is_file():
                reason = "The original source file is unavailable for rebuild"
                if doc_id:
                    self._set_private_status(user_id, doc_id, "failed", error_message=reason)
                failures.append({"doc_id": doc_id, "reason": reason})
                continue
            try:
                file_data = self._read_source_bytes(document, storage_path)
                snapshot = self._start_ingestion(user_id, doc_id, file_data, job_type="rebuild", force=True)
                if snapshot.get("job_id"):
                    self._set_private_status(user_id, doc_id, "processing")
                    jobs.append(snapshot)
                else:
                    failures.append({"doc_id": doc_id, "reason": "Could not create rebuild task"})
            except Exception:
                logger.exception("Could not queue rebuild for %s", doc_id)
                failures.append({"doc_id": doc_id, "reason": "Could not create rebuild task"})
        return {"success": bool(jobs) or not documents, "message": "Knowledge rebuild tasks were queued", "jobs": jobs, "queued_count": len(jobs), "failed_count": len(failures), "failures": failures}

    def delete_indexed_document(self, user_id: str, doc_id: str) -> bool:
        """Delete a source's retrieval chunks for permanent purge only."""
        return self._store.delete_document(scope=KnowledgeScope.USER, owner_id=user_id, document_id=doc_id)

    def index_stats(self, user_id: str) -> Dict[str, Any]:
        """Return scoped index diagnostics for the workspace maintenance view."""
        return self._store.stats(scope=KnowledgeScope.USER, owner_id=user_id)

    def queue_private_index_encryption_rebuilds(self, *, limit: int = 500) -> Dict[str, Any]:
        """Queue durable rebuilds for private indexes whose Chroma bodies are not encrypted.

        Inputs: catalog records marked with an older index protection version.
        Outputs: queued job count and visible failures. Called during application
        startup after private source-storage maintenance has completed. Side
        effects: removes obsolete chunks before the durable worker creates the
        encrypted replacement, preferring temporary unavailability to plaintext.
        """
        if self._catalog is None or self._cipher is None or self._lifecycle_repository is None:
            return {"queued_count": 0, "failed": []}
        queued = 0
        failures: List[Dict[str, str]] = []
        for document in self._catalog.private_documents_requiring_index_encryption(
            index_version=self._cipher.VERSION, limit=limit
        ):
            if not bool(document.get("is_active", True)) or str(document.get("parse_status") or "") != "completed":
                continue
            document_id = str(document.get("doc_id") or "")
            owner_id = str(document.get("owner_id") or "")
            source_path = self._record_storage_path(document)
            if not document_id or not owner_id or not source_path.is_file():
                failures.append({"document_id": document_id, "reason": "source_file_unavailable"})
                continue
            try:
                source = self._read_source_bytes(document, source_path)
                snapshot = self._start_ingestion(owner_id, document_id, source, job_type="rebuild", force=True)
                if not snapshot.get("job_id"):
                    failures.append({"document_id": document_id, "reason": "job_creation_failed"})
                    continue
                if not self._store.delete_document(
                    scope=KnowledgeScope.USER, owner_id=owner_id, document_id=document_id
                ):
                    failures.append({"document_id": document_id, "reason": "obsolete_index_delete_failed"})
                    continue
                self._set_private_status(
                    owner_id, document_id, "processing", chroma_ids=[], index_encryption_version="queued"
                )
                queued += 1
            except Exception:
                logger.exception("Could not queue private encrypted index rebuild for %s", document_id)
                failures.append({"document_id": document_id, "reason": "index_rebuild_queue_failed"})
        return {"queued_count": queued, "failed": failures}

    def migrate_private_source_storage(self, *, limit: int = 500) -> Dict[str, Any]:
        """Move every private source onto the current encrypted opaque-path policy.

        Inputs: private catalog rows that need source encryption or whose managed
        path still exposes a historical filename. Outputs: encryption, relocation,
        and failure counts. Called before workers resume. Side effects: plaintext
        bytes are replaced with Fernet ciphertext, encrypted files move to the
        document-id .bin path, and SQLite records the new version and path together.
        """
        if self._catalog is None or self._cipher is None:
            return {"migrated_count": 0, "relocated_count": 0, "already_secure_count": 0, "failed": []}
        migrated = 0
        relocated = 0
        already_secure = 0
        failures: List[Dict[str, str]] = []
        storage_root = self.storage_path.resolve()
        for document in self._catalog.private_documents_requiring_source_storage_migration(
            source_version=self._cipher.VERSION, limit=limit
        ):
            document_id = str(document.get("doc_id") or "")
            owner_id = str(document.get("owner_id") or "")
            source_path = self._record_storage_path(document)
            if not document_id or not owner_id or not source_path.is_file():
                failures.append({"document_id": document_id, "reason": "source_file_unavailable"})
                continue
            try:
                source_path = source_path.resolve(strict=True)
                if storage_root not in source_path.parents:
                    raise RuntimeError("source_path_outside_managed_storage")
                target_path = self._storage_path(owner_id, document_id, "").resolve()
                if storage_root not in target_path.parents:
                    raise RuntimeError("target_path_outside_managed_storage")
                stored_bytes = source_path.read_bytes()
                if self._cipher.appears_encrypted(stored_bytes):
                    self._cipher.decrypt(stored_bytes)
                    already_secure += 1
                else:
                    temporary_path = source_path.with_name(source_path.name + ".encrypting")
                    try:
                        temporary_path.write_bytes(self._cipher.encrypt(stored_bytes))
                        os.replace(temporary_path, source_path)
                    finally:
                        if temporary_path.exists():
                            temporary_path.unlink()
                    migrated += 1

                moved = False
                if source_path != target_path:
                    if target_path.exists():
                        raise FileExistsError("canonical_source_path_already_exists")
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(source_path, target_path)
                    moved = True
                try:
                    updated = self._catalog.set_encryption_versions(
                        owner_id=owner_id,
                        document_id=document_id,
                        source_version=self._cipher.VERSION,
                        storage_path=str(target_path),
                    )
                    if not updated:
                        raise RuntimeError("source_storage_catalog_update_failed")
                except Exception:
                    if moved and target_path.is_file() and not source_path.exists():
                        os.replace(target_path, source_path)
                    raise
                if moved:
                    relocated += 1
            except Exception:
                logger.exception("Could not migrate private knowledge source storage for %s", document_id)
                failures.append({"document_id": document_id, "reason": "source_storage_migration_failed"})
        return {
            "migrated_count": migrated,
            "relocated_count": relocated,
            "already_secure_count": already_secure,
            "failed": failures,
        }

    def _start_ingestion(self, user_id: str, doc_id: str, file_data: bytes, *, job_type: str = "ingest", force: bool = False) -> Dict[str, Any]:
        if self._lifecycle_repository is None:
            return {}
        return self._lifecycle_repository.start_ingestion(
            document_id=doc_id,
            owner_id=user_id,
            content_fingerprint=hashlib.sha256(file_data).hexdigest(),
            source_size=len(file_data),
            index_version="knowledge-store-v1",
            job_type=job_type,
            force=force,
        )

    async def _enrich_image(self, file_data: bytes, file_name: str, parse_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self._image_describer is not None:
                content = await self._image_describer(file_data, file_name)
            else:
                from services.ai_services.vision_caption import describe_image_for_knowledge
                content = await describe_image_for_knowledge(file_data, file_name, settings=self._settings)
        except Exception:
            logger.exception("Image knowledge extraction failed for %s", file_name)
            return {"success": False, "error": "图片资料暂时无法识别。请启用支持看图的 AI 服务，或改用可复制文本的文档。"}
        content = str(content or "").strip()
        if not content:
            return {"success": False, "error": "图片资料没有提取到可用于检索的内容。请上传更清晰的图片，或改用文本资料。"}
        enriched = dict(parse_result)
        enriched.update({"success": True, "content": content, "extraction_method": "vision"})
        enriched.pop("requires_vision_enrichment", None)
        return enriched

    def _validate_file(self, file_data: bytes, file_name: str) -> Dict[str, Any]:
        if len(file_data) > self.max_file_size:
            return {"valid": False, "message": f"文件大小超过限制，最大允许 {self.max_file_size / 1024 / 1024:.1f}MB"}
        file_type = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        supported = document_parser.get_supported_types()
        if file_type and file_type not in supported:
            return {"valid": False, "message": f"不支持的文件类型: {file_type}，支持的类型: {', '.join(supported)}"}
        if not file_data:
            return {"valid": False, "message": "空文件不允许上传"}
        return {"valid": True}

    def _save_document_file(self, user_id: str, file_data: bytes, file_name: str) -> str:
        doc_id = str(uuid.uuid4())
        user_dir = self.storage_path / user_id
        user_dir.mkdir(exist_ok=True)
        stored_data = self._cipher.encrypt(file_data) if self._cipher else file_data
        self._storage_path(user_id, doc_id, file_name).write_bytes(stored_data)
        return doc_id

    def _record_storage_path(self, document: Dict[str, Any]) -> Path:
        """Resolve a catalog storage path without depending on the process CWD.

        Historical rows may hold a relative user_documents path. New rows hold
        an absolute opaque path. Both resolve under this manager's storage root;
        paths outside that root are rejected by source-storage maintenance.
        """
        raw_path = Path(str(document.get("storage_path") or ""))
        if raw_path.is_absolute():
            return raw_path
        if raw_path.parts and raw_path.parts[0].lower() == self.storage_path.name.lower():
            return self.storage_path.parent / raw_path
        return self.storage_path / raw_path

    def _storage_path(self, user_id: str, doc_id: str, file_name: str) -> Path:
        del file_name
        # The catalog is the only place that keeps the user-visible file name.
        # Managed storage names contain no user-supplied text and are encrypted.
        return self.storage_path / user_id / f"{doc_id}.bin"

    def _read_source_bytes(self, document: Dict[str, Any], storage_path: Path) -> bytes:
        """Read a current encrypted private source inside trusted worker code."""
        if self._cipher is None:
            raise RuntimeError("Private knowledge source encryption is not configured")
        version = str(document.get("encryption_version") or "none")
        if version != self._cipher.VERSION:
            raise RuntimeError("Private knowledge source requires encryption migration")
        return self._cipher.decrypt(storage_path.read_bytes())

    @staticmethod
    def _generate_title(file_name: str, metadata: Dict[str, Any]) -> str:
        del metadata
        base = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        return base.replace("_", " ").replace("-", " ").title()

    def _create_private_document(self, *, user_id: str, doc_id: str, title: str, file_name: str, file_type: str, file_size: int, storage_path: str, tags: List[str]) -> None:
        if self._catalog is not None:
            self._catalog.create_document(visibility="private", document_id=doc_id, owner_id=user_id, title=title, file_name=file_name, file_type=file_type, file_size=file_size, storage_path=storage_path, encryption_version=self._cipher.VERSION if self._cipher else "none", tags=tags)
            return
        self.db.add_user_document(doc_id=doc_id, user_id=user_id, title=title, original_name=file_name, file_type=file_type, file_size=file_size, storage_path=storage_path, content_preview="", tags=tags)

    def _get_private_document(self, user_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
        if self._catalog is not None:
            return self._catalog.get_document(visibility="private", document_id=doc_id, owner_id=user_id, include_archived=True, viewer_id=user_id)
        return self.db.get_user_document(user_id, doc_id)

    def _list_private_documents(self, user_id: str) -> List[Dict[str, Any]]:
        if self._catalog is not None:
            return list(self._catalog.list_documents(owner_id=user_id, source="uploads", retention="active", limit=500)["documents"])
        return list(self.db.get_user_documents(user_id, limit=500))

    def _set_private_status(self, user_id: str, doc_id: str, status: str, *, chroma_ids: Optional[List[str]] = None, content_preview: Optional[str] = None, vector_collection: Optional[str] = None, error_message: Optional[str] = None, index_encryption_version: Optional[str] = None) -> bool:
        if self._catalog is not None:
            return self._catalog.set_processing_state(visibility="private", document_id=doc_id, owner_id=user_id, parse_status=status, chroma_ids=chroma_ids, content_preview=content_preview, index_collection=vector_collection, error_message=error_message, index_encryption_version=index_encryption_version)
        return self.db.update_user_document_status(doc_id, status, chroma_ids=chroma_ids, content_preview=content_preview, vector_collection=vector_collection, error_message=error_message)

    def _failed(self, user_id: str, doc_id: str, message: str) -> Dict[str, Any]:
        self._set_private_status(user_id, doc_id, "failed", error_message=message, index_encryption_version="none")
        return {"success": False, "error": message}

    def _cancelled(self, user_id: str, doc_id: str) -> Dict[str, Any]:
        """Persist a cooperative cancellation with the same terminal meaning as its job.

        Inputs: the owner and source identity whose currently leased job reached a
        cancellation checkpoint. Outputs: the worker result understood by
        ``KnowledgeJobService``. Called by: document-processing checkpoints.
        Side effects: updates the source catalog only; the job worker writes the
        durable job's terminal ``cancelled`` state with its lease. Invariant: a
        user-requested cancellation is never represented as a parsing failure.
        """
        self._set_private_status(user_id, doc_id, "cancelled")
        return {"cancelled": True}
