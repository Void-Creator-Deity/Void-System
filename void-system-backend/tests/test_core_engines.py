import unittest

from core.knowledge_contracts import KnowledgeAnswer, KnowledgeChunk, KnowledgeQuery, KnowledgeScope
from modules.knowledge.engine import KnowledgeEngine
from modules.knowledge.responders import GroundedKnowledgeResponder
from modules.knowledge.quality import DeterministicEvidenceQualityPolicy
from modules.knowledge.retrieval import EvidenceReranker, ReciprocalRankFusionIndex
from core.planning_contracts import PlanRequest, PlanResult, PlannedTask, EvaluationRequest, EvaluationResult


class FakeIndex:
    def search(self, query):
        return [KnowledgeChunk(
            chunk_id="c1",
            document_id="d1",
            owner_id=query.owner_id or "u1",
            text="hello knowledge",
            scope=KnowledgeScope.USER,
            score=0.9,
        )]

    def delete_document(self, owner_id, document_id, scope):
        return True


class FakeResponder:
    async def answer(self, query, chunks):
        return KnowledgeAnswer(answer="ok", citations=list(chunks), confidence=0.9)


class RecordingResponder(FakeResponder):
    def __init__(self):
        self.calls = 0

    async def answer(self, query, chunks):
        self.calls += 1
        return await super().answer(query, chunks)


class FakeTraceRecorder:
    def __init__(self):
        self.calls = []

    def record_retrieval(self, **kwargs):
        self.calls.append(kwargs)
        return "trace-1"


class FakeKnowledgeUseRecorder:
    def __init__(self):
        self.calls = []

    def record_knowledge_use(self, **kwargs):
        self.calls.append(kwargs)
        return "use-1"


class StaticIndex:
    def __init__(self, chunks):
        self.chunks = chunks

    def search(self, query):
        return self.chunks

    def delete_document(self, owner_id, document_id, scope):
        return True


class FakeGenerator:
    def __init__(self):
        self.evidence = ""

    async def generate(self, question, evidence):
        self.evidence = evidence
        return "基于证据的回答 [S1]"


class FakePlanner:
    def plan(self, request):
        return PlanResult(
            response="planned",
            tasks=[PlannedTask(title=request.topic, description="desc")],
            mode=request.mode,
        )


class FakeEvaluator:
    def evaluate(self, request):
        return EvaluationResult(status="pass", feedback="good", score=90, suggested_rewards={"coins": 10})


class CoreEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_knowledge_engine_searches_and_answers(self):
        engine = KnowledgeEngine(index=FakeIndex(), responder=FakeResponder())
        result = await engine.ask(KnowledgeQuery(question="hello", owner_id="u1"))
        self.assertEqual(result.answer, "ok")
        self.assertEqual(len(result.citations), 1)
        self.assertEqual(result.citations[0].document_id, "d1")


    async def test_knowledge_engine_records_validated_evidence_trace(self):
        recorder = FakeTraceRecorder()
        engine = KnowledgeEngine(
            index=FakeIndex(),
            responder=FakeResponder(),
            trace_recorder=recorder,
        )

        result = await engine.ask(KnowledgeQuery(question="hello", owner_id="u1"))

        self.assertEqual(result.metadata["trace_id"], "trace-1")
        self.assertEqual(recorder.calls[0]["owner_id"], "u1")
        self.assertEqual(recorder.calls[0]["citations"][0]["document_id"], "d1")

    async def test_knowledge_engine_records_only_aggregate_use_outcome(self):
        recorder = FakeKnowledgeUseRecorder()
        engine = KnowledgeEngine(
            index=FakeIndex(),
            responder=FakeResponder(),
            use_recorder=recorder,
        )

        result = await engine.ask(
            KnowledgeQuery(question="hello knowledge", owner_id="u1")
        )

        self.assertEqual(result.metadata["knowledge_use_event_id"], "use-1")
        self.assertEqual(len(recorder.calls), 1)
        self.assertEqual(
            recorder.calls[0],
            {
                "owner_id": "u1",
                "mode": "hybrid",
                "candidate_count": 1,
                "ranked_count": 1,
                "source_count": 1,
                "citation_count": 1,
                "answerable": True,
            },
        )
        self.assertNotIn("hello knowledge", str(recorder.calls[0]))

    async def test_knowledge_engine_search_uses_index(self):
        engine = KnowledgeEngine(index=FakeIndex(), responder=FakeResponder())
        chunks = engine.search(KnowledgeQuery(question="q", owner_id="u1"))
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "hello knowledge")


    async def test_knowledge_engine_declines_irrelevant_evidence_without_calling_model(self):
        responder = RecordingResponder()
        engine = KnowledgeEngine(
            index=StaticIndex([
                KnowledgeChunk(
                    chunk_id="c1",
                    document_id="d1",
                    owner_id="u1",
                    text="The garden opens on Sunday and has roses.",
                    scope=KnowledgeScope.USER,
                )
            ]),
            responder=responder,
        )

        result = await engine.ask(
            KnowledgeQuery(question="What is the deployment approval schedule?", owner_id="u1")
        )

        self.assertEqual(responder.calls, 0)
        self.assertEqual(result.citations, [])
        self.assertEqual(result.metadata["evidence_quality"]["reason"], "insufficient_relevance")
        self.assertFalse(result.metadata["evidence_quality"]["answerable"])

    async def test_knowledge_engine_limits_repeated_sources_and_exposes_quality(self):
        chunks = [
            KnowledgeChunk(
                chunk_id="d1-c1",
                document_id="d1",
                owner_id="u1",
                text="Release plan: production deployment is approved on Monday.",
                scope=KnowledgeScope.USER,
            ),
            KnowledgeChunk(
                chunk_id="d1-c2",
                document_id="d1",
                owner_id="u1",
                text="Release plan: rollback is reviewed by the same team.",
                scope=KnowledgeScope.USER,
            ),
            KnowledgeChunk(
                chunk_id="d2-c1",
                document_id="d2",
                owner_id="u1",
                text="Release plan: security approval is required before production deployment.",
                scope=KnowledgeScope.USER,
            ),
        ]
        engine = KnowledgeEngine(
            index=StaticIndex(chunks),
            responder=FakeResponder(),
            evidence_policy=DeterministicEvidenceQualityPolicy(max_per_document=1),
        )

        result = await engine.ask(KnowledgeQuery(question="release plan", owner_id="u1"))

        self.assertEqual({citation.document_id for citation in result.citations}, {"d1", "d2"})
        quality = result.metadata["evidence_quality"]
        self.assertTrue(quality["answerable"])
        self.assertEqual(quality["source_count"], 2)
        self.assertEqual(quality["usable_count"], 2)


class KnowledgeRetrievalTests(unittest.IsolatedAsyncioTestCase):
    def _chunk(self, chunk_id, document_id, text, score=None):
        return KnowledgeChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            owner_id="u1",
            text=text,
            scope=KnowledgeScope.USER,
            score=score,
        )

    def test_reciprocal_rank_fusion_combines_channels(self):
        shared = self._chunk("shared", "d1", "Python testing guide")
        semantic = StaticIndex([shared, self._chunk("semantic", "d2", "Unit tests")])
        lexical = StaticIndex([shared, self._chunk("lexical", "d3", "Python guide")])
        index = ReciprocalRankFusionIndex([semantic, lexical])

        results = index.search(KnowledgeQuery(question="Python", owner_id="u1", top_k=3))

        self.assertEqual(results[0].chunk_id, "shared")
        self.assertEqual(len(results[0].metadata["retrieval_channels"]), 2)

    def test_reranker_limits_duplicate_document_chunks(self):
        chunks = [
            self._chunk("c1", "d1", "Python testing architecture"),
            self._chunk("c2", "d1", "Python testing patterns"),
            self._chunk("c3", "d2", "Python testing checklist"),
        ]
        reranked = EvidenceReranker(max_per_document=1).rerank(
            KnowledgeQuery(question="Python testing", owner_id="u1", top_k=3), chunks
        )

        self.assertEqual({chunk.document_id for chunk in reranked}, {"d1", "d2"})

    async def test_grounded_responder_uses_supplied_evidence_once(self):
        generator = FakeGenerator()
        responder = GroundedKnowledgeResponder(generator)
        chunk = self._chunk("c1", "d1", "The project uses hybrid retrieval.")

        result = await responder.answer(
            KnowledgeQuery(question="How is retrieval implemented?", owner_id="u1"), [chunk]
        )

        self.assertIn("[S1]", generator.evidence)
        self.assertEqual(result.citations, [chunk])
        self.assertTrue(result.metadata["grounded"])


class PlanningContractTests(unittest.TestCase):
    def test_planning_engine_contract_shape(self):
        result = FakePlanner().plan(PlanRequest(topic="learn testing", mode="workflow_chain"))
        self.assertEqual(result.response, "planned")
        self.assertEqual(result.tasks[0].title, "learn testing")

    def test_evaluation_engine_contract_shape(self):
        result = FakeEvaluator().evaluate(EvaluationRequest(task={}, submission={}, user_stats={}))
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.suggested_rewards["coins"], 10)


if __name__ == "__main__":
    unittest.main()
