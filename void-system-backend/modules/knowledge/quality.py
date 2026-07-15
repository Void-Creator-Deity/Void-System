
"""Deterministic, conservative answerability checks for retrieved knowledge."""
from __future__ import annotations

from dataclasses import replace
import re
from typing import Dict, List, Sequence, Set, Tuple

from core.knowledge_contracts import EvidenceAssessment, KnowledgeAnswer, KnowledgeChunk, KnowledgeQuery

from modules.knowledge.retrieval import lexical_terms


_ENGLISH_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "that", "the", "to",
    "was", "what", "when", "where", "which", "who", "why", "with", "you",
}


def _evidence_relevance(question: str, text: str) -> float:
    """Measure support using meaningful query terms, not English function words."""
    query_terms = lexical_terms(question)
    meaningful_terms = {
        term for term in query_terms
        if term not in _ENGLISH_STOPWORDS and (len(term) > 1 or "\\u4e00" <= term <= "\\u9fff")
    }
    if not meaningful_terms:
        meaningful_terms = query_terms
    if not meaningful_terms:
        return 0.0
    overlap = meaningful_terms & lexical_terms(text)
    coverage = len(overlap) / len(meaningful_terms)
    phrase_bonus = 0.2 if question.strip().lower() in text.lower() else 0.0
    return min(1.0, coverage + phrase_bonus)


class DeterministicEvidenceQualityPolicy:
    """Keep unsupported context away from the answer generator.

    The policy deliberately uses deterministic signals available from every index:
    query-to-chunk lexical support, duplicate suppression, and source diversity.
    It can later be replaced by a learned answerability model without changing
    the product-facing knowledge engine contract.
    """

    def __init__(
        self,
        *,
        min_relevance: float = 0.16,
        max_per_document: int = 2,
    ) -> None:
        self._min_relevance = min(1.0, max(0.0, min_relevance))
        self._max_per_document = max(1, max_per_document)

    def assess(
        self, query: KnowledgeQuery, chunks: Sequence[KnowledgeChunk]
    ) -> EvidenceAssessment:
        question = query.question.strip()
        if not question:
            return EvidenceAssessment(
                answerable=False,
                reason="empty_question",
                candidate_count=len(chunks),
                usable_count=0,
                source_count=0,
                top_relevance=0.0,
                mean_relevance=0.0,
            )

        selected: List[KnowledgeChunk] = []
        relevance_scores: List[float] = []
        seen_text: Set[str] = set()
        per_document: Dict[str, int] = {}
        nonempty_candidates = 0

        for chunk in chunks:
            text = chunk.text.strip()
            if not text:
                continue
            nonempty_candidates += 1
            relevance = _evidence_relevance(question, text)
            if relevance < self._min_relevance:
                continue

            fingerprint = re.sub(r"\\s+", " ", text.lower())[:500]
            if fingerprint in seen_text:
                continue
            document_id = chunk.document_id or chunk.chunk_id
            document_count = per_document.get(document_id, 0)
            if document_count >= self._max_per_document:
                continue

            metadata = dict(chunk.metadata)
            metadata["evidence_relevance"] = round(relevance, 4)
            selected.append(replace(chunk, metadata=metadata))
            relevance_scores.append(relevance)
            seen_text.add(fingerprint)
            per_document[document_id] = document_count + 1

        if not selected:
            reason = "no_evidence" if nonempty_candidates == 0 else "insufficient_relevance"
            return EvidenceAssessment(
                answerable=False,
                reason=reason,
                candidate_count=len(chunks),
                usable_count=0,
                source_count=0,
                top_relevance=0.0,
                mean_relevance=0.0,
            )

        source_count = len(per_document)
        top_relevance = max(relevance_scores)
        mean_relevance = sum(relevance_scores) / len(relevance_scores)
        return EvidenceAssessment(
            answerable=True,
            reason="supported" if source_count > 1 else "limited_source_diversity",
            candidate_count=len(chunks),
            usable_count=len(selected),
            source_count=source_count,
            top_relevance=top_relevance,
            mean_relevance=mean_relevance,
            evidence=selected,
        )



def answer_support(answer: KnowledgeAnswer) -> Dict[str, int | str]:
    """Map internal evidence metadata to a small, user-facing API state."""
    quality = answer.metadata.get("evidence_quality", {})
    answerable = bool(quality.get("answerable", bool(answer.citations)))
    source_count = int(quality.get("source_count", len({item.document_id for item in answer.citations})))
    return {
        "status": "ready" if answerable else "needs_more_context",
        "source_count": max(0, source_count),
    }
