"""Legacy adapters connecting current Chroma and LangChain implementations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from core.runtime_settings import RuntimeSettings
from core.knowledge_workspace_contracts import UserKnowledgeRepository

from core.knowledge_contracts import (
    GroundedGenerator, IngestSource, KnowledgeChunk, KnowledgeIndex,
    KnowledgeQuery, KnowledgeScope,
)
from modules.knowledge.responders import GroundedKnowledgeResponder
from modules.knowledge.retrieval import EvidenceReranker, ReciprocalRankFusionIndex, lexical_score


def _to_chunk(doc: Any, query: KnowledgeQuery, index: int, score: float | None = None) -> KnowledgeChunk:
    metadata: Dict[str, Any] = dict(getattr(doc, "metadata", {}) or {})
    doc_id = str(metadata.get("doc_id") or metadata.get("document_id") or "")
    return KnowledgeChunk(
        chunk_id=str(metadata.get("chunk_id") or f"{doc_id}:{metadata.get('chunk_index', index)}"),
        document_id=doc_id,
        owner_id=str(metadata.get("user_id") or query.owner_id or ""),
        text=str(getattr(doc, "page_content", "")),
        scope=KnowledgeScope.USER,
        score=score,
        title=metadata.get("title"),
        file_name=metadata.get("file_name"),
        chunk_index=metadata.get("chunk_index"),
        metadata=metadata,
    )


class LegacyUserVectorIndex(KnowledgeIndex):
    """Semantic retrieval backed by the existing user Chroma collection."""

    def __init__(self, vector_manager: Any, repository: UserKnowledgeRepository) -> None:
        self._vector_manager = vector_manager
        self._repository = repository

    def search(self, query: KnowledgeQuery) -> Sequence[KnowledgeChunk]:
        if not query.owner_id:
            return []
        active_ids = list(self._repository.active_document_ids(query.owner_id, query.document_ids))
        if not active_ids:
            return []
        collection = self._vector_manager.get_user_collection(query.owner_id)
        filter_dict = {"doc_id": {"$in": active_ids}}
        fetch_limit = max(query.top_k * 3, query.top_k)
        try:
            results = collection.similarity_search_with_relevance_scores(
                query=query.question, k=fetch_limit, filter=filter_dict
            )
            return [
                _to_chunk(doc, query, index, float(score))
                for index, (doc, score) in enumerate(results[: query.top_k])
            ]
        except Exception:
            docs = self._vector_manager.search_user_documents(
                user_id=query.owner_id,
                query=query.question,
                top_k=fetch_limit,
                doc_ids=active_ids,
            )
            return [_to_chunk(doc, query, index) for index, doc in enumerate(docs[: query.top_k])]

    def delete_document(self, owner_id: str, document_id: str, scope: KnowledgeScope) -> bool:
        if scope != KnowledgeScope.USER:
            return False
        return bool(self._vector_manager.delete_document_vectors(owner_id, document_id))


class LegacyUserLexicalIndex(KnowledgeIndex):
    """Keyword recall over Chroma documents, independent of embeddings."""

    def __init__(
        self, vector_manager: Any, repository: UserKnowledgeRepository, scan_limit: int = 2500
    ) -> None:
        self._vector_manager = vector_manager
        self._repository = repository
        self._scan_limit = max(100, scan_limit)

    def search(self, query: KnowledgeQuery) -> Sequence[KnowledgeChunk]:
        if not query.owner_id:
            return []
        active_ids = list(self._repository.active_document_ids(query.owner_id, query.document_ids))
        if not active_ids:
            return []
        collection = self._vector_manager.get_user_collection(query.owner_id)
        where = {"doc_id": {"$in": active_ids}}
        try:
            raw = collection.get(
                where=where,
                limit=self._scan_limit,
                include=["documents", "metadatas"],
            )
        except Exception:
            return []
        documents = raw.get("documents") or []
        metadatas = raw.get("metadatas") or []
        ranked = []
        for index, text in enumerate(documents):
            score = lexical_score(query.question, str(text or ""))
            if score <= 0:
                continue
            metadata = dict(metadatas[index] or {}) if index < len(metadatas) else {}
            doc_id = str(metadata.get("doc_id") or metadata.get("document_id") or "")
            chunk_id = str(metadata.get("chunk_id") or f"{doc_id}:{metadata.get('chunk_index', index)}")
            ranked.append(KnowledgeChunk(
                chunk_id=chunk_id,
                document_id=doc_id,
                owner_id=str(metadata.get("user_id") or query.owner_id),
                text=str(text or ""),
                scope=KnowledgeScope.USER,
                score=score,
                title=metadata.get("title"),
                file_name=metadata.get("file_name"),
                chunk_index=metadata.get("chunk_index"),
                metadata=metadata,
            ))
        ranked.sort(key=lambda chunk: chunk.score or 0.0, reverse=True)
        return ranked[: query.top_k]

    def delete_document(self, owner_id: str, document_id: str, scope: KnowledgeScope) -> bool:
        return False


class LegacyLangChainGroundedGenerator(GroundedGenerator):
    """LangChain model adapter that only synthesizes from supplied evidence."""

    def __init__(self, settings: Optional[RuntimeSettings] = None) -> None:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from services.ai_services.llm_factory import get_chat_llm

        prompt = ChatPromptTemplate.from_template("""你是个人知识工作区的回答助手。请严格依据证据回答，不得补造事实。

规则：
1. 对关键结论使用 [S1]、[S2] 形式标注证据。
2. 证据不足时明确说明缺少什么，不要用常识填空。
3. 合并重复信息，指出证据间的冲突或不确定性。
4. 先给直接结论，再给必要说明，语言自然清晰。

证据：
{evidence}

问题：{question}
""")
        self._chain = prompt | get_chat_llm(temperature=0.2, settings=settings) | StrOutputParser()

    async def generate(self, question: str, evidence: str) -> str:
        return str(await self._chain.ainvoke({"question": question, "evidence": evidence}))


class LegacyUserDocumentIngestor:
    def __init__(self, document_manager: Any) -> None:
        self._document_manager = document_manager

    async def ingest(self, source: IngestSource) -> Dict[str, Any]:
        return await self._document_manager.upload_and_process_document(
            user_id=source.owner_id,
            file_data=source.content,
            file_name=source.file_name,
            title=source.title,
            tags=list(source.tags),
        )


def build_legacy_user_knowledge_engine(
    document_manager: Any,
    vector_manager: Any,
    repository: UserKnowledgeRepository,
    trace_recorder: Any = None,
    use_recorder: Any = None,
    settings: Optional[RuntimeSettings] = None,
):
    """Compose hybrid retrieval and grounded generation over supplied adapters."""
    from modules.knowledge.engine import KnowledgeEngine

    vector_index = LegacyUserVectorIndex(vector_manager, repository)
    lexical_index = LegacyUserLexicalIndex(vector_manager, repository)
    return KnowledgeEngine(
        index=ReciprocalRankFusionIndex([vector_index, lexical_index]),
        reranker=EvidenceReranker(max_per_document=2),
        responder=GroundedKnowledgeResponder(LegacyLangChainGroundedGenerator(settings=settings)),
        ingestor=LegacyUserDocumentIngestor(document_manager),
        trace_recorder=trace_recorder,
        use_recorder=use_recorder,
    )


class LegacySystemVectorIndex(KnowledgeIndex):
    """Semantic retrieval over application-owned system knowledge documents."""

    def __init__(self, manager: Any) -> None:
        self._manager = manager

    def search(self, query: KnowledgeQuery) -> Sequence[KnowledgeChunk]:
        if KnowledgeScope.SYSTEM not in query.scopes:
            return []
        catalog = _system_document_catalog(self._manager, query)
        if not catalog:
            return []
        try:
            matches = self._manager.vector_db.similarity_search_with_relevance_scores(
                query.question,
                k=max(query.top_k * 3, query.top_k),
            )
        except Exception:
            try:
                matches = [(document, None) for document in self._manager.vector_db.similarity_search(
                    query.question,
                    k=max(query.top_k * 3, query.top_k),
                )]
            except Exception:
                return []
        chunks = []
        for index, (document, score) in enumerate(matches):
            chunk = _to_system_chunk(document, query, index, catalog, score)
            if chunk is not None:
                chunks.append(chunk)
            if len(chunks) >= query.top_k:
                break
        return chunks

    def delete_document(self, owner_id: str, document_id: str, scope: KnowledgeScope) -> bool:
        if scope != KnowledgeScope.SYSTEM:
            return False
        self._manager.vector_db.delete(where={"doc_id": document_id})
        return True


class LegacySystemLexicalIndex(KnowledgeIndex):
    """Keyword recall over the system vector store, constrained by active catalog rows."""

    def __init__(self, manager: Any, scan_limit: int = 2500) -> None:
        self._manager = manager
        self._scan_limit = max(100, scan_limit)

    def search(self, query: KnowledgeQuery) -> Sequence[KnowledgeChunk]:
        if KnowledgeScope.SYSTEM not in query.scopes:
            return []
        catalog = _system_document_catalog(self._manager, query)
        if not catalog:
            return []
        try:
            raw = self._manager.vector_db.get(
                limit=self._scan_limit,
                include=["documents", "metadatas"],
            )
        except Exception:
            return []
        documents = raw.get("documents") or []
        metadatas = raw.get("metadatas") or []
        ranked = []
        for index, text in enumerate(documents):
            score = lexical_score(query.question, str(text or ""))
            if score <= 0:
                continue
            metadata = dict(metadatas[index] or {}) if index < len(metadatas) else {}
            document = type("SystemKnowledgeDocument", (), {
                "page_content": str(text or ""),
                "metadata": metadata,
            })()
            chunk = _to_system_chunk(document, query, index, catalog, score)
            if chunk is not None:
                ranked.append(chunk)
        ranked.sort(key=lambda chunk: chunk.score or 0.0, reverse=True)
        return ranked[: query.top_k]

    def delete_document(self, owner_id: str, document_id: str, scope: KnowledgeScope) -> bool:
        return False


def _system_document_catalog(manager: Any, query: KnowledgeQuery) -> Dict[str, Dict[str, Any]]:
    requested_tags = query.filters.get("tags") if isinstance(query.filters, dict) else None
    tags = [str(tag).strip() for tag in requested_tags or [] if str(tag).strip()]
    documents = manager.db.list_system_rag_documents(tags or None)
    allowed_ids = {str(document_id) for document_id in query.document_ids or []}
    return {
        str(document.get("id") or document.get("doc_id") or ""): document
        for document in documents
        if not allowed_ids or str(document.get("id") or document.get("doc_id") or "") in allowed_ids
    }


def _to_system_chunk(
    document: Any,
    query: KnowledgeQuery,
    index: int,
    catalog: Dict[str, Dict[str, Any]],
    score: float | None = None,
) -> Optional[KnowledgeChunk]:
    metadata: Dict[str, Any] = dict(getattr(document, "metadata", {}) or {})
    document_id = str(metadata.get("doc_id") or metadata.get("document_id") or "")
    record = catalog.get(document_id)
    if record is None:
        return None
    enriched_metadata = {
        **metadata,
        "tags": list(record.get("tags") or []),
        "description": record.get("description") or "",
    }
    return KnowledgeChunk(
        chunk_id=str(metadata.get("chunk_id") or f"{document_id}:{metadata.get('chunk_index', index)}"),
        document_id=document_id,
        owner_id="system",
        text=str(getattr(document, "page_content", "")),
        scope=KnowledgeScope.SYSTEM,
        score=float(score) if score is not None else None,
        title=record.get("title"),
        file_name=record.get("file_name") or metadata.get("file_name"),
        chunk_index=metadata.get("chunk_index"),
        metadata=enriched_metadata,
    )


def build_legacy_system_knowledge_engine(
    manager: Any,
    settings: Optional[RuntimeSettings] = None,
):
    """Compose the shared hybrid retrieval pipeline over system knowledge."""
    from modules.knowledge.engine import KnowledgeEngine

    return KnowledgeEngine(
        index=ReciprocalRankFusionIndex([
            LegacySystemVectorIndex(manager),
            LegacySystemLexicalIndex(manager),
        ]),
        reranker=EvidenceReranker(max_per_document=2),
        responder=GroundedKnowledgeResponder(LegacyLangChainGroundedGenerator(settings=settings)),
    )
