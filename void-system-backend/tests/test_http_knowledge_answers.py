
"""Contract tests for the product-facing knowledge answer payload."""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from api.http.routers.library import ask_library
from core.knowledge_contracts import KnowledgeAnswer, KnowledgeChunk, KnowledgeScope


class StaticAnswerEngine:
    def __init__(self, answer):
        self.answer = answer

    async def ask(self, query):
        return self.answer


def _knowledge_answer(answerable=True):
    citations = []
    if answerable:
        citations.append(KnowledgeChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            owner_id="member-1",
            text="The project review is held on Monday.",
            scope=KnowledgeScope.USER,
            title="Project Guide",
        ))
    return KnowledgeAnswer(
        answer="The project review is held on Monday." if answerable else "Please add more context.",
        citations=citations,
        confidence=0.8 if answerable else 0.0,
        metadata={
            "evidence_quality": {
                "answerable": answerable,
                "source_count": len(citations),
            }
        },
    )


class KnowledgeAnswerHttpContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_personal_answer_returns_support_state(self):
        resources = SimpleNamespace(
            engine=StaticAnswerEngine(_knowledge_answer(True)),
            workspace=SimpleNamespace(
                stats=lambda user_id: {"completed_documents": 1}
            ),
        )

        response = await ask_library(
            question="When is the project review?",
            include_global_shared=False,
            document_ids=None,
            tags=None,
            current_user={"user_id": "member-1"},
            resources=resources,
        )

        self.assertEqual(response.data["support"], {"status": "ready", "source_count": 1})
        self.assertEqual(response.data["sources"][0]["document_id"], "doc-1")

    async def test_shared_answer_returns_needs_more_context(self):
        resources = SimpleNamespace(engine=StaticAnswerEngine(_knowledge_answer(False)))

        response = await ask_library(
            question="What is the policy?",
            include_global_shared=True,
            document_ids=None,
            tags=None,
            current_user={"user_id": "member-1"},
            resources=resources,
        )

        self.assertEqual(
            response.data["support"],
            {"status": "needs_more_context", "source_count": 0},
        )
