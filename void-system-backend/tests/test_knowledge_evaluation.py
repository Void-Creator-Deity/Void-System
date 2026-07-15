
"""Regression tests for offline knowledge-quality metrics."""
from __future__ import annotations

import unittest

from core.knowledge_contracts import KnowledgeAnswer, KnowledgeChunk, KnowledgeScope
from modules.knowledge.evaluation import KnowledgeEvaluationCase, KnowledgeEvaluationRunner
from modules.knowledge.quality import answer_support


class FakeEvaluationEngine:
    def __init__(self, answers):
        self._answers = answers

    async def ask(self, query):
        return self._answers[query.question]


def _answer(document_ids, answerable=True):
    return KnowledgeAnswer(
        answer="answer" if answerable else "insufficient evidence",
        citations=[
            KnowledgeChunk(
                chunk_id=f"{document_id}-chunk",
                document_id=document_id,
                owner_id="member-1",
                text="evidence",
                scope=KnowledgeScope.USER,
            )
            for document_id in document_ids
        ],
        metadata={"evidence_quality": {"answerable": answerable}},
    )


class KnowledgeAnswerSupportTests(unittest.TestCase):
    def test_maps_internal_evidence_state_to_stable_product_status(self):
        self.assertEqual(
            answer_support(_answer(["source-1"], answerable=True)),
            {"status": "ready", "source_count": 1},
        )
        self.assertEqual(
            answer_support(_answer([], answerable=False)),
            {"status": "needs_more_context", "source_count": 0},
        )


class KnowledgeEvaluationRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_reports_citation_and_refusal_metrics(self):
        engine = FakeEvaluationEngine({
            "project policy": _answer(["policy-doc", "extra-doc"]),
            "unrelated request": _answer([], answerable=False),
        })
        runner = KnowledgeEvaluationRunner(engine)

        report = await runner.run([
            KnowledgeEvaluationCase(
                case_id="supported",
                question="project policy",
                expected_document_ids=["policy-doc"],
            ),
            KnowledgeEvaluationCase(
                case_id="refuse",
                question="unrelated request",
                should_answer=False,
            ),
        ])

        self.assertEqual(report.case_count, 2)
        self.assertEqual(report.citation_recall, 1.0)
        self.assertEqual(report.citation_precision, 0.5)
        self.assertEqual(report.refusal_accuracy, 1.0)
        self.assertEqual(report.answerability_accuracy, 1.0)
        self.assertTrue(report.results[0].source_hit)
        self.assertTrue(report.results[1].refusal_correct)

    async def test_marks_wrong_source_and_unsupported_answer_as_regressions(self):
        engine = FakeEvaluationEngine({
            "project policy": _answer(["wrong-doc"]),
            "unrelated request": _answer(["wrong-doc"], answerable=True),
        })
        runner = KnowledgeEvaluationRunner(engine)

        report = await runner.run([
            KnowledgeEvaluationCase(
                case_id="wrong-source",
                question="project policy",
                expected_document_ids=["policy-doc"],
            ),
            KnowledgeEvaluationCase(
                case_id="wrong-refusal",
                question="unrelated request",
                should_answer=False,
            ),
        ])

        self.assertEqual(report.citation_recall, 0.0)
        self.assertEqual(report.citation_precision, 0.0)
        self.assertEqual(report.refusal_accuracy, 0.0)
        self.assertEqual(report.answerability_accuracy, 0.5)
        self.assertFalse(report.results[0].source_hit)
        self.assertFalse(report.results[1].refusal_correct)
