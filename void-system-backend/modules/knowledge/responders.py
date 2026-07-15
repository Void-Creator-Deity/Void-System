"""Grounded answer synthesis over retrieved evidence."""
from __future__ import annotations

from typing import List, Sequence

from core.knowledge_contracts import (
    GroundedGenerator, KnowledgeAnswer, KnowledgeChunk, KnowledgeQuery, KnowledgeResponder,
)
from modules.knowledge.retrieval import lexical_score


class GroundedKnowledgeResponder(KnowledgeResponder):
    """Build bounded evidence, invoke one generator, and return real citations."""

    def __init__(self, generator: GroundedGenerator, max_context_chars: int = 14000) -> None:
        self._generator = generator
        self._max_context_chars = max(1000, max_context_chars)

    async def answer(self, query: KnowledgeQuery, chunks: Sequence[KnowledgeChunk]) -> KnowledgeAnswer:
        selected, evidence = self._build_evidence(chunks)
        if not selected:
            return KnowledgeAnswer(
                answer="当前知识库中没有找到足以回答该问题的内容。你可以补充资料或调整问题后重试。",
                citations=[],
                confidence=0.0,
                metadata={"grounded": True, "reason": "no_evidence"},
            )
        answer = (await self._generator.generate(query.question, evidence)).strip()
        if not answer:
            answer = "现有证据不足以形成可靠回答。"
        coverage = max((lexical_score(query.question, chunk.text) for chunk in selected), default=0.0)
        diversity = len({chunk.document_id for chunk in selected})
        confidence = min(0.95, 0.35 + coverage * 0.45 + min(diversity, 3) * 0.05)
        return KnowledgeAnswer(
            answer=answer,
            citations=selected,
            confidence=round(confidence, 3),
            metadata={
                "grounded": True,
                "evidence_count": len(selected),
                "document_count": diversity,
                "context_chars": len(evidence),
            },
        )

    def _build_evidence(self, chunks: Sequence[KnowledgeChunk]):
        selected: List[KnowledgeChunk] = []
        parts: List[str] = []
        used = 0
        for number, chunk in enumerate(chunks, 1):
            text = chunk.text.strip()
            if not text:
                continue
            label = chunk.title or chunk.file_name or chunk.document_id or "未命名资料"
            header = f"[S{number}] {label}"
            remaining = self._max_context_chars - used - len(header) - 2
            if remaining <= 0:
                break
            bounded_text = text[:remaining]
            parts.append(f"{header}\n{bounded_text}")
            selected.append(chunk)
            used += len(header) + len(bounded_text) + 2
        return selected, "\n\n".join(parts)
