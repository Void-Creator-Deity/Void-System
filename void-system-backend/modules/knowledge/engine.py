"""
Knowledge Engine facade.

This module is the new product-facing seam for all knowledge-backed features.
It keeps the current implementation working while giving us one place to add
hybrid retrieval, reranking, citation validation, GraphRAG-style summaries, and
index rebuild jobs later.
"""
from __future__ import annotations

from typing import Optional, Sequence

from core.knowledge_contracts import (
    IngestSource,
    EvidenceQualityPolicy,
    KnowledgeAnswer,
    KnowledgeChunk,
    KnowledgeIndex,
    KnowledgeIngestor,
    KnowledgeQuery,
    KnowledgeResponder,
    KnowledgeTraceRecorder,
    KnowledgeUseEventRecorder,
    NullReranker,
    Reranker,
)
from modules.knowledge.quality import DeterministicEvidenceQualityPolicy


class KnowledgeEngine:
    """Deep module hiding retrieval, reranking, and answer synthesis details."""

    def __init__(
        self,
        *,
        index: KnowledgeIndex,
        responder: KnowledgeResponder,
        ingestor: Optional[KnowledgeIngestor] = None,
        reranker: Optional[Reranker] = None,
        evidence_policy: Optional[EvidenceQualityPolicy] = None,
        trace_recorder: Optional[KnowledgeTraceRecorder] = None,
        use_recorder: Optional[KnowledgeUseEventRecorder] = None,
    ) -> None:
        self._index = index
        self._responder = responder
        self._ingestor = ingestor
        self._reranker = reranker or NullReranker()
        self._evidence_policy = evidence_policy or DeterministicEvidenceQualityPolicy()
        self._trace_recorder = trace_recorder
        self._use_recorder = use_recorder

    async def ask(self, query: KnowledgeQuery) -> KnowledgeAnswer:
        """Search, rank, assess support, and synthesize only when evidence is adequate."""
        chunks = list(self._index.search(query))
        ranked = list(self._reranker.rerank(query, chunks))
        assessment = self._evidence_policy.assess(query, ranked)
        quality_metadata = assessment.as_metadata()

        if not assessment.answerable:
            answer = KnowledgeAnswer(
                answer=(
                    "当前资料不足以可靠回答这个问题。请补充相关资料，"
                    "或换一种更具体的问法后再试。"
                ),
                citations=[],
                confidence=0.0,
                metadata={"grounded": True, "reason": assessment.reason},
            )
        else:
            answer = await self._responder.answer(query, assessment.evidence)

        allowed = {chunk.chunk_id: chunk for chunk in assessment.evidence}
        citations = []
        seen = set()
        for citation in answer.citations:
            if citation.chunk_id in allowed and citation.chunk_id not in seen:
                citations.append(allowed[citation.chunk_id])
                seen.add(citation.chunk_id)
        metadata = dict(answer.metadata)
        metadata.update({
            "retrieved_candidates": len(chunks),
            "ranked_evidence": len(ranked),
            "validated_citations": len(citations),
            "evidence_quality": quality_metadata,
        })
        if self._trace_recorder is not None and query.owner_id:
            try:
                metadata["trace_id"] = self._trace_recorder.record_retrieval(
                    owner_id=query.owner_id,
                    question=query.question,
                    mode=query.mode,
                    candidate_count=len(chunks),
                    ranked_count=len(ranked),
                    citations=[
                        {
                            "document_id": citation.document_id,
                            "chunk_id": citation.chunk_id,
                            "title": citation.title or citation.file_name,
                            "chunk_index": citation.chunk_index,
                        }
                        for citation in citations
                    ],
                )
            except Exception:
                # Answering remains available when observability storage is degraded.
                metadata["trace_recorded"] = False
        if self._use_recorder is not None and query.owner_id:
            try:
                metadata["knowledge_use_event_id"] = self._use_recorder.record_knowledge_use(
                    owner_id=query.owner_id,
                    mode=query.mode,
                    candidate_count=len(chunks),
                    ranked_count=len(ranked),
                    source_count=len({citation.document_id for citation in citations}),
                    citation_count=len(citations),
                    answerable=assessment.answerable,
                )
            except Exception:
                # Behavioral telemetry is optional and never changes the answer path.
                metadata["knowledge_use_recorded"] = False

        return KnowledgeAnswer(
            answer=answer.answer,
            citations=citations,
            confidence=answer.confidence,
            metadata=metadata,
        )

    def search(self, query: KnowledgeQuery) -> Sequence[KnowledgeChunk]:
        """Expose retrieval for UI search and diagnostics without answer synthesis."""
        chunks = list(self._index.search(query))
        return list(self._reranker.rerank(query, chunks))

    async def ingest(self, source: IngestSource) -> dict:
        """Store and index a source document through the configured pipeline."""
        if self._ingestor is None:
            raise RuntimeError("Knowledge ingestion is not configured")
        return await self._ingestor.ingest(source)
