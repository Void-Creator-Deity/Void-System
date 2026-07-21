"""Single Chroma implementation for personal and shared knowledge.

This adapter owns collection naming, chunking, retrieval primitives, and the
one-way migration from the retired anonymous shared collection. Product modules
provide eligibility and ownership; they never select a Chroma collection.
"""
from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.knowledge_contracts import KnowledgeChunk, KnowledgeQuery, KnowledgeRetrievalError, KnowledgeScope
from core.runtime_settings import RuntimeSettings
from modules.knowledge.encrypted_storage import KnowledgeSourceCipher
from services.ai_services.llm_factory import get_embeddings

logger = logging.getLogger("void-system.knowledge.chroma")
SYSTEM_COLLECTION = "system_knowledge"
LEGACY_SYSTEM_COLLECTION = "langchain"
_SAFE_COLLECTION_PART = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class IndexWriteResult:
    """Stable result returned after replacing a document's indexed chunks."""

    chunk_ids: Sequence[str]
    collection: str


class ChromaKnowledgeStore:
    """Persist and retrieve scoped knowledge with exactly one collection policy.

    Inputs: application-owned runtime settings. Outputs: indexing, semantic and
    lexical recall, deletion, diagnostics, and old-system collection migration.
    Called by: personal/shared document modules and retrieval indexes.
    Invariant: callers cannot use Chroma's implicit default collection.
    """

    def __init__(self, settings: RuntimeSettings, *, cipher: Optional[KnowledgeSourceCipher] = None) -> None:
        self._path = Path(settings.get_chroma_path())
        self._cipher = cipher or KnowledgeSourceCipher(settings, Path(settings.BASE_DIR) / "user_documents")
        self._path.mkdir(parents=True, exist_ok=True)
        self._embeddings = get_embeddings(settings=settings)
        self._collections: Dict[str, Chroma] = {}
        self._native_clients: list[Any] = []
        self._default_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self._code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=150,
            separators=["\ndef ", "\nclass ", "\nimport ", "\nfrom ", "\n\n", "\n", " ", ""],
        )
        self._markdown_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\n# ", "\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""],
        )

    def close(self) -> None:
        """Release cached Chroma clients when a runtime or test store is finished.

        Inputs: none. Outputs: none. Called by application shutdown and isolated
        tests. Side effects: stops each native Chroma client once and clears this
        adapter's collection cache, which releases Windows file handles without
        exposing the native client to product modules.
        """
        clients = [getattr(collection, "_client", None) for collection in self._collections.values()]
        clients.extend(self._native_clients)
        released_systems: set[int] = set()
        for client in clients:
            if client is None:
                continue
            try:
                system = getattr(client, "_system", None)
                system_id = id(system) if system is not None else id(client)
                if system_id in released_systems:
                    continue
                released_systems.add(system_id)
                close = getattr(client, "close", None)
                if callable(close):
                    close()
                    continue
                stop = getattr(system, "stop", None)
                if callable(stop):
                    stop()
            except Exception:
                logger.debug("Could not release a Chroma client cleanly", exc_info=True)
        self._collections.clear()
        self._native_clients.clear()

    def collection_name(self, scope: KnowledgeScope, owner_id: Optional[str] = None) -> str:
        """Return the only valid persistent collection name for a scope."""
        if scope == KnowledgeScope.SYSTEM:
            return SYSTEM_COLLECTION
        if scope == KnowledgeScope.USER:
            if not owner_id or not _SAFE_COLLECTION_PART.fullmatch(owner_id):
                raise ValueError("A safe owner id is required for personal knowledge")
            # Existing personal data already uses this key, so migration does not
            # duplicate or rewrite user embeddings merely to rename storage.
            return f"user_{owner_id}_docs"
        raise ValueError(f"Knowledge scope {scope.value!r} is not persistent")

    def index_text(self, *, scope: KnowledgeScope, owner_id: str, document_id: str, text: str, metadata: Optional[Mapping[str, Any]] = None) -> IndexWriteResult:
        """Replace one document's chunks; retries cannot leave mixed versions."""
        content = str(text or "").strip()
        if not content:
            raise ValueError("Knowledge text must not be empty")
        chunks = self._splitter_for(str((metadata or {}).get("file_type") or "")).split_text(content)
        if not chunks:
            raise ValueError("Knowledge text did not produce searchable chunks")
        self.delete_document(scope=scope, owner_id=owner_id, document_id=document_id)
        base = self._scalar_metadata(metadata or {})
        base.update({
            "doc_id": str(document_id), "document_id": str(document_id), "scope": scope.value,
            "owner_id": str(owner_id), "chunk_count": len(chunks),
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        })
        if scope == KnowledgeScope.USER:
            base["user_id"] = str(owner_id)
        ids: list[str] = []
        documents: list[Document] = []
        encrypted_texts: list[str] = []
        if scope == KnowledgeScope.USER:
            # Titles and file names already come from the SQLite catalog at read
            # time. Keeping only the minimum routing metadata in Chroma avoids a
            # second plaintext copy of user-provided identity data.
            base.pop("title", None)
            base.pop("file_name", None)
            base["content_encryption"] = self._cipher.VERSION
        for index, chunk_text in enumerate(chunks):
            chunk_id = self._chunk_id(scope, owner_id, document_id, index, chunk_text)
            ids.append(chunk_id)
            metadata_for_chunk = {**base, "chunk_index": index, "chunk_id": chunk_id}
            documents.append(Document(page_content=chunk_text, metadata=metadata_for_chunk))
            if scope == KnowledgeScope.USER:
                encrypted_texts.append(self._cipher.encrypt_text(chunk_text))
        collection = self._collection(scope, owner_id)
        if scope == KnowledgeScope.USER:
            # Chroma persists ciphertext, while embeddings are calculated from the
            # trusted in-memory chunks. Semantic retrieval therefore remains useful
            # without retaining a plaintext document body on disk.
            embeddings = self._embeddings.embed_documents(chunks)
            collection._collection.add(
                ids=ids,
                documents=encrypted_texts,
                metadatas=[document.metadata for document in documents],
                embeddings=embeddings,
            )
        else:
            collection.add_documents(documents, ids=ids)
        return IndexWriteResult(ids, self.collection_name(scope, owner_id))

    def semantic_search(self, *, query: KnowledgeQuery, scope: KnowledgeScope, catalog: Mapping[str, Mapping[str, Any]]) -> Sequence[KnowledgeChunk]:
        """Recall only catalog-eligible chunks through the configured embeddings."""
        if not catalog:
            return []
        owner_id = self._owner_for(scope, query)
        where = {"doc_id": {"$in": list(catalog)}}
        try:
            collection = self._collection(scope, owner_id)
            try:
                distance_matches = collection.similarity_search_with_score(
                    query.question,
                    k=max(query.top_k * 3, query.top_k),
                    filter=where,
                )
                # Providers can return unnormalized embeddings. Convert raw
                # distance locally instead of asking Chroma for a misleading
                # 0..1 relevance score based on a fixed normalization policy.
                matches = [
                    (document, 1.0 / (1.0 + max(0.0, float(distance))))
                    for document, distance in distance_matches
                ]
            except Exception:
                matches = [
                    (document, None)
                    for document in collection.similarity_search(
                        query.question,
                        k=max(query.top_k * 3, query.top_k),
                        filter=where,
                    )
                ]
        except Exception as exc:
            self._raise_retrieval_failure(f"{scope.value}_semantic", exc)
        return self._to_chunks(query, scope, matches, catalog)[: query.top_k]

    def lexical_search(self, *, query: KnowledgeQuery, scope: KnowledgeScope, catalog: Mapping[str, Mapping[str, Any]], scan_limit: int = 2500) -> Sequence[KnowledgeChunk]:
        """Recall only catalog-eligible chunks through deterministic lexical scoring."""
        if not catalog:
            return []
        owner_id = self._owner_for(scope, query)
        try:
            raw = self._collection(scope, owner_id).get(where={"doc_id": {"$in": list(catalog)}}, limit=max(100, scan_limit), include=["documents", "metadatas"])
        except Exception as exc:
            self._raise_retrieval_failure(f"{scope.value}_lexical", exc)
        from modules.knowledge.retrieval import lexical_score
        ranked: list[KnowledgeChunk] = []
        documents = raw.get("documents") or []
        metadata_values = raw.get("metadatas") or []
        for index, text in enumerate(documents):
            metadata = dict(metadata_values[index] or {}) if index < len(metadata_values) else {}
            plaintext = self._decode_index_text(str(text or ""), metadata, scope=scope)
            score = lexical_score(query.question, plaintext)
            if score <= 0:
                continue
            ranked.extend(self._to_chunks(query, scope, [(Document(page_content=str(text or ""), metadata=metadata), score)], catalog))
        ranked.sort(key=lambda item: item.score or 0.0, reverse=True)
        return ranked[: query.top_k]

    def delete_document(self, *, scope: KnowledgeScope, owner_id: str, document_id: str) -> bool:
        """Delete all chunks for one document and return a retry-safe outcome."""
        try:
            self._collection(scope, owner_id).delete(where={"doc_id": str(document_id)})
            return True
        except Exception:
            logger.exception("Could not remove indexed knowledge document %s", document_id)
            return False

    def stats(self, *, scope: KnowledgeScope, owner_id: str) -> Dict[str, Any]:
        """Return diagnostics without exposing Chroma clients beyond this adapter."""
        try:
            raw = self._collection(scope, owner_id).get(include=["metadatas"])
            metadatas = raw.get("metadatas") or []
            document_ids = {str(item.get("doc_id")) for item in metadatas if item and item.get("doc_id")}
            return {"collection_name": self.collection_name(scope, owner_id), "total_vectors": len(raw.get("ids") or []), "total_documents": len(document_ids)}
        except Exception as exc:
            logger.exception("Could not read knowledge diagnostics")
            return {"collection_name": self.collection_name(scope, owner_id), "total_vectors": 0, "total_documents": 0, "error": type(exc).__name__}

    def reconcile_catalog(self, *, scope: KnowledgeScope, owner_id: str, allowed_document_ids: Sequence[str]) -> int:
        """Remove chunks whose documents are no longer present in the scoped catalog."""
        try:
            collection = self._collection(scope, owner_id)
            raw = collection.get(include=["metadatas"])
            ids = raw.get("ids") or []
            metadata_values = raw.get("metadatas") or []
            allowed = {str(item) for item in allowed_document_ids}
            stale = [str(item_id) for item_id, metadata in zip(ids, metadata_values) if str((metadata or {}).get("doc_id") or "") not in allowed]
            if stale:
                collection.delete(ids=stale)
            return len(stale)
        except Exception as exc:
            logger.error("Knowledge catalog reconciliation failed", exc_info=exc)
            raise

    def migrate_legacy_shared_collection(self, active_documents: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
        """One-way migrate valid old shared chunks into the named system collection.

        SQLite catalog rows are authoritative. Untracked chunks were not valid
        product documents, so they are removed together with the retired store.
        The native client is owned by this store and released during application
        shutdown, preventing Windows file locks from outliving the store lifecycle.
        """
        client = chromadb.PersistentClient(path=str(self._path))
        self._native_clients.append(client)
        if LEGACY_SYSTEM_COLLECTION not in {item.name for item in client.list_collections()}:
            return {"migrated": False, "reason": "legacy_collection_absent", "copied_chunks": 0}
        source = client.get_collection(LEGACY_SYSTEM_COLLECTION)
        raw = source.get(include=["documents", "metadatas", "embeddings"])
        eligible: list[tuple[str, str, Dict[str, Any], Any]] = []
        orphan_ids: list[str] = []
        ids = raw.get("ids") or []
        documents = raw.get("documents") or []
        metadata_values = raw.get("metadatas") or []
        embeddings = raw.get("embeddings")
        if embeddings is None:
            embeddings = []
        for index, raw_id in enumerate(ids):
            metadata = dict(metadata_values[index] or {}) if index < len(metadata_values) else {}
            document_id = str(metadata.get("doc_id") or metadata.get("document_id") or "")
            if document_id not in active_documents:
                orphan_ids.append(str(raw_id))
                continue
            record = active_documents[document_id]
            metadata.update({
                "doc_id": document_id,
                "document_id": document_id,
                "scope": KnowledgeScope.SYSTEM.value,
                "owner_id": "system",
                "title": str(record.get("title") or metadata.get("title") or ""),
                "file_name": str(record.get("file_name") or metadata.get("file_name") or ""),
            })
            eligible.append((
                str(raw_id),
                str(documents[index] or ""),
                self._scalar_metadata(metadata),
                embeddings[index] if index < len(embeddings) else None,
            ))
        target = client.get_or_create_collection(SYSTEM_COLLECTION)
        known = set(target.get(include=[]).get("ids") or [])
        missing = [item for item in eligible if item[0] not in known]
        if missing:
            target.add(
                ids=[item[0] for item in missing],
                documents=[item[1] for item in missing],
                metadatas=[item[2] for item in missing],
                embeddings=[item[3] for item in missing],
            )
        expected = {item[0] for item in eligible}
        verified = target.get(ids=list(expected), include=["metadatas"])
        found = set(verified.get("ids") or [])
        metadata_by_id = {
            str(item_id): dict(item or {})
            for item_id, item in zip(verified.get("ids") or [], verified.get("metadatas") or [])
        }
        if found != expected or any(
            str(metadata_by_id[item_id].get("doc_id") or "") not in active_documents
            for item_id in expected
        ):
            raise RuntimeError("Shared knowledge migration verification failed")
        client.delete_collection(LEGACY_SYSTEM_COLLECTION)
        self._collections.pop(SYSTEM_COLLECTION, None)
        logger.info("Migrated shared knowledge: copied=%s removed_orphans=%s", len(eligible), len(orphan_ids))
        return {
            "migrated": True,
            "copied_chunks": len(eligible),
            "removed_orphan_chunks": len(orphan_ids),
            "target_collection": SYSTEM_COLLECTION,
        }

    def _collection(self, scope: KnowledgeScope, owner_id: str) -> Chroma:
        name = self.collection_name(scope, owner_id)
        if name not in self._collections:
            self._collections[name] = Chroma(collection_name=name, persist_directory=str(self._path), embedding_function=self._embeddings)
        return self._collections[name]

    def _splitter_for(self, file_type: str) -> RecursiveCharacterTextSplitter:
        normalized = file_type.lower().lstrip(".")
        if normalized in {"py", "js", "java", "cpp", "c", "ts", "go", "rs", "php"}:
            return self._code_splitter
        if normalized in {"md", "markdown"}:
            return self._markdown_splitter
        return self._default_splitter

    @staticmethod
    def _owner_for(scope: KnowledgeScope, query: KnowledgeQuery) -> str:
        if scope == KnowledgeScope.SYSTEM:
            return "system"
        if not query.owner_id:
            raise ValueError("Personal knowledge retrieval requires an owner")
        return query.owner_id

    def _to_chunks(self, query: KnowledgeQuery, scope: KnowledgeScope, documents: Iterable[tuple[Document, Optional[float]]], catalog: Mapping[str, Mapping[str, Any]]) -> list[KnowledgeChunk]:
        result: list[KnowledgeChunk] = []
        for index, (document, score) in enumerate(documents):
            metadata = dict(document.metadata or {})
            document_id = str(metadata.get("doc_id") or metadata.get("document_id") or "")
            record = catalog.get(document_id)
            if record is None:
                continue
            text = self._decode_index_text(str(document.page_content or ""), metadata, scope=scope)
            result.append(KnowledgeChunk(chunk_id=str(metadata.get("chunk_id") or f"{document_id}:{metadata.get('chunk_index', index)}"), document_id=document_id, owner_id=(query.owner_id or "") if scope == KnowledgeScope.USER else "system", text=text, scope=scope, score=float(score) if score is not None else None, title=str(record.get("title") or metadata.get("title") or "") or None, file_name=str(record.get("file_name") or metadata.get("file_name") or "") or None, chunk_index=metadata.get("chunk_index"), metadata={**metadata, "tags": list(record.get("tags") or [])}))
        return result

    def _decode_index_text(self, text: str, metadata: Mapping[str, Any], *, scope: KnowledgeScope) -> str:
        """Decrypt a current private Chroma body after scoped catalog eligibility."""
        if scope != KnowledgeScope.USER:
            return text
        if str(metadata.get("content_encryption") or "") != self._cipher.VERSION:
            self._raise_retrieval_failure(
                "private_content_encryption",
                RuntimeError("Private Chroma content requires encryption migration"),
            )
        try:
            return self._cipher.decrypt_text(text)
        except Exception as exc:
            self._raise_retrieval_failure("private_content_decryption", exc)

    @staticmethod
    def _chunk_id(scope: KnowledgeScope, owner_id: str, document_id: str, index: int, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"void-knowledge:{scope.value}:{owner_id}:{document_id}:{index}:{digest}"))

    @staticmethod
    def _scalar_metadata(values: Mapping[str, Any]) -> Dict[str, Any]:
        return {str(key): value if isinstance(value, (str, int, float, bool)) else str(value) for key, value in values.items() if value is not None}

    @staticmethod
    def _raise_retrieval_failure(component: str, exc: Exception) -> None:
        logger.error("Knowledge retrieval failed in %s: %s", component, exc, exc_info=True)
        raise KnowledgeRetrievalError(component) from exc
