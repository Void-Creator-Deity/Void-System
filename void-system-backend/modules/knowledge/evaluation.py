
"""Offline regression metrics for knowledge-answering behavior."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Sequence

from core.knowledge_contracts import KnowledgeQuery
from modules.knowledge.engine import KnowledgeEngine


@dataclass(frozen=True)
class KnowledgeEvaluationCase:
    """One deterministic expectation for a knowledge query."""

    case_id: str
    question: str
    expected_document_ids: Sequence[str] = field(default_factory=list)
    should_answer: bool = True
    owner_id: str | None = None
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeEvaluationResult:
    """Per-case evidence outcome, intentionally independent of answer wording."""

    case_id: str
    answerable: bool
    citation_document_ids: Sequence[str]
    expected_document_ids: Sequence[str]
    source_hit: bool | None
    refusal_correct: bool | None


@dataclass(frozen=True)
class KnowledgeEvaluationReport:
    """Aggregate source-grounding and refusal metrics."""

    case_count: int
    citation_precision: float | None
    citation_recall: float | None
    refusal_accuracy: float | None
    answerability_accuracy: float
    results: Sequence[KnowledgeEvaluationResult]


class KnowledgeEvaluationRunner:
    """Evaluate retrieval and answerability without grading free-form model prose."""

    def __init__(self, engine: KnowledgeEngine) -> None:
        self._engine = engine

    async def run(self, cases: Sequence[KnowledgeEvaluationCase]) -> KnowledgeEvaluationReport:
        results = []
        answerability_correct = 0
        expected_citation_total = 0
        expected_citation_hits = 0
        returned_citation_total = 0
        returned_citation_hits = 0
        refusal_cases = 0
        refusal_correct = 0

        for case in cases:
            answer = await self._engine.ask(
                KnowledgeQuery(
                    question=case.question,
                    owner_id=case.owner_id,
                    filters=case.filters,
                )
            )
            quality = answer.metadata.get("evidence_quality", {})
            answerable = bool(quality.get("answerable", bool(answer.citations)))
            cited_ids = tuple(sorted({citation.document_id for citation in answer.citations}))
            expected_ids = tuple(sorted(set(case.expected_document_ids)))
            expected_set = set(expected_ids)
            cited_set = set(cited_ids)
            source_hit = None
            refusal = None

            if case.should_answer:
                source_hit = bool(expected_set & cited_set) if expected_set else bool(cited_set)
                expected_citation_total += len(expected_set)
                expected_citation_hits += len(expected_set & cited_set)
                returned_citation_total += len(cited_set)
                returned_citation_hits += len(expected_set & cited_set)
                answerability_correct += int(answerable)
            else:
                refusal_cases += 1
                refusal = not answerable and not cited_set
                refusal_correct += int(refusal)
                answerability_correct += int(not answerable)

            results.append(KnowledgeEvaluationResult(
                case_id=case.case_id,
                answerable=answerable,
                citation_document_ids=cited_ids,
                expected_document_ids=expected_ids,
                source_hit=source_hit,
                refusal_correct=refusal,
            ))

        citation_precision = (
            round(returned_citation_hits / returned_citation_total, 4)
            if returned_citation_total else None
        )
        citation_recall = (
            round(expected_citation_hits / expected_citation_total, 4)
            if expected_citation_total else None
        )
        refusal_accuracy = (
            round(refusal_correct / refusal_cases, 4)
            if refusal_cases else None
        )
        answerability_accuracy = (
            round(answerability_correct / len(cases), 4)
            if cases else 1.0
        )
        return KnowledgeEvaluationReport(
            case_count=len(cases),
            citation_precision=citation_precision,
            citation_recall=citation_recall,
            refusal_accuracy=refusal_accuracy,
            answerability_accuracy=answerability_accuracy,
            results=results,
        )
