"""Multi-stage retrieval and deterministic evidence ranking."""
from __future__ import annotations

from dataclasses import replace
import math
import re
from typing import Dict, Iterable, List, Sequence, Set

from core.knowledge_contracts import KnowledgeChunk, KnowledgeIndex, KnowledgeQuery, KnowledgeScope, Reranker


_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]")


def lexical_terms(text: str) -> Set[str]:
    """Tokenize Latin words plus Chinese unigrams and adjacent bigrams."""
    raw = [token.lower() for token in _TOKEN_RE.findall(text or "")]
    terms = set(raw)
    chinese = [token for token in raw if len(token) == 1 and "\u4e00" <= token <= "\u9fff"]
    terms.update(a + b for a, b in zip(chinese, chinese[1:]))
    return terms


def lexical_score(question: str, text: str) -> float:
    query_terms = lexical_terms(question)
    if not query_terms:
        return 0.0
    text_terms = lexical_terms(text)
    overlap = query_terms & text_terms
    coverage = len(overlap) / len(query_terms)
    phrase_bonus = 0.2 if question.strip().lower() in (text or "").lower() else 0.0
    return min(1.0, coverage + phrase_bonus)


class ReciprocalRankFusionIndex(KnowledgeIndex):
    """Fuse independent retrieval channels without assuming comparable scores."""

    def __init__(self, indexes: Sequence[KnowledgeIndex], rank_constant: int = 60, expansion: int = 4) -> None:
        if not indexes:
            raise ValueError("At least one knowledge index is required")
        self._indexes = list(indexes)
        self._rank_constant = max(1, rank_constant)
        self._expansion = max(1, expansion)

    def search(self, query: KnowledgeQuery) -> Sequence[KnowledgeChunk]:
        candidate_query = replace(query, top_k=max(query.top_k, query.top_k * self._expansion))
        fused_scores: Dict[str, float] = {}
        chunks: Dict[str, KnowledgeChunk] = {}
        channels: Dict[str, List[str]] = {}
        for channel_number, index in enumerate(self._indexes, 1):
            channel = type(index).__name__
            for rank, chunk in enumerate(index.search(candidate_query), 1):
                key = chunk.chunk_id or f"{chunk.document_id}:{chunk.chunk_index}:{hash(chunk.text)}"
                fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (self._rank_constant + rank)
                chunks.setdefault(key, chunk)
                channels.setdefault(key, []).append(channel)
        ranked_keys = sorted(fused_scores, key=fused_scores.get, reverse=True)
        results: List[KnowledgeChunk] = []
        for key in ranked_keys[: candidate_query.top_k]:
            chunk = chunks[key]
            metadata = dict(chunk.metadata)
            metadata["retrieval_channels"] = channels[key]
            metadata["fusion_score"] = fused_scores[key]
            results.append(replace(chunk, score=fused_scores[key], metadata=metadata))
        return results

    def delete_document(self, owner_id: str, document_id: str, scope: KnowledgeScope) -> bool:
        results = [index.delete_document(owner_id, document_id, scope) for index in self._indexes]
        return any(results)


class EvidenceReranker(Reranker):
    """Rank for lexical fit, retrieval support, and document diversity."""

    def __init__(self, max_per_document: int = 2) -> None:
        self._max_per_document = max(1, max_per_document)

    def rerank(self, query: KnowledgeQuery, chunks: Sequence[KnowledgeChunk]) -> Sequence[KnowledgeChunk]:
        scored = []
        for rank, chunk in enumerate(chunks):
            lexical = lexical_score(query.question, chunk.text)
            retrieval = 1.0 / (1.0 + rank)
            if chunk.score is not None and math.isfinite(float(chunk.score)):
                retrieval = max(retrieval, min(1.0, max(0.0, float(chunk.score) * 20)))
            score = 0.65 * lexical + 0.35 * retrieval
            metadata = dict(chunk.metadata)
            metadata["lexical_score"] = lexical
            metadata["rerank_score"] = score
            scored.append(replace(chunk, score=score, metadata=metadata))
        scored.sort(key=lambda item: item.score or 0.0, reverse=True)
        selected: List[KnowledgeChunk] = []
        per_document: Dict[str, int] = {}
        seen_text: Set[str] = set()
        for chunk in scored:
            fingerprint = re.sub(r"\s+", " ", chunk.text.strip().lower())[:500]
            if not fingerprint or fingerprint in seen_text:
                continue
            count = per_document.get(chunk.document_id, 0)
            if count >= self._max_per_document:
                continue
            seen_text.add(fingerprint)
            per_document[chunk.document_id] = count + 1
            selected.append(chunk)
            if len(selected) >= query.top_k:
                break
        return selected
