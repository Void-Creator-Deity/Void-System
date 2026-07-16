import tempfile
import unittest
from pathlib import Path

from adapters.sqlite.knowledge_lifecycle_repository import SQLiteKnowledgeLifecycleRepository
from database import Database


class KnowledgeLifecycleRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "knowledge.db")
        self.repository = SQLiteKnowledgeLifecycleRepository(self.database.get_connection)
        connection = self.database.get_connection()
        try:
            connection.executemany(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                [("user-1", "user-one"), ("user-2", "user-two")],
            )
            connection.commit()
        finally:
            connection.close()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_ingestion_lifecycle_tracks_completion_for_its_owner(self) -> None:
        started = self.repository.start_ingestion(
            document_id="doc-1",
            owner_id="user-1",
            content_fingerprint="fingerprint",
            source_size=42,
            index_version="test-index-v1",
        )

        self.assertFalse(started["duplicate"])
        self.assertTrue(
            self.repository.update_ingestion(
                job_id=started["job_id"],
                owner_id="user-1",
                status="completed",
                chunk_count=3,
                index_version="test-index-v1",
            )
        )
        self.assertFalse(
            self.repository.update_ingestion(
                job_id=started["job_id"],
                owner_id="user-2",
                status="failed",
            )
        )

        lifecycle = self.repository.latest_ingestion(document_id="doc-1", owner_id="user-1")
        self.assertEqual(lifecycle["status"], "completed")
        self.assertEqual(lifecycle["chunk_count"], 3)
        self.assertIsNotNone(lifecycle["completed_at"])

    def test_retrieval_traces_are_owner_scoped(self) -> None:
        trace_id = self.repository.record_retrieval(
            owner_id="user-1",
            question="What is the plan?",
            mode="hybrid",
            candidate_count=4,
            ranked_count=2,
            citations=[{"document_id": "doc-1", "chunk_id": "chunk-1"}],
        )

        traces = self.repository.list_retrievals(owner_id="user-1")
        self.assertEqual(traces[0]["trace_id"], trace_id)
        self.assertEqual(traces[0]["citations"][0]["document_id"], "doc-1")
        self.assertEqual(self.repository.list_retrievals(owner_id="user-2"), [])


    def test_profile_knowledge_use_summary_is_reliable_and_owner_scoped(self) -> None:
        self.repository.record_knowledge_use(
            owner_id="user-1", mode="hybrid", candidate_count=4, ranked_count=2,
            source_count=1, citation_count=1, answerable=True,
        )
        self.repository.record_knowledge_use(
            owner_id="user-1", mode="hybrid", candidate_count=4, ranked_count=0,
            source_count=0, citation_count=0, answerable=False,
        )
        self.repository.record_knowledge_use(
            owner_id="user-2", mode="hybrid", candidate_count=3, ranked_count=2,
            source_count=1, citation_count=1, answerable=True,
        )

        summary = self.repository.summarize_profile_knowledge_use("user-1")
        self.assertEqual(summary["knowledge_use_count"], 2)
        self.assertEqual(summary["answerable_use_count"], 1)
        self.assertEqual(summary["cited_use_count"], 1)
        self.assertEqual(summary["reliable_use_count"], 1)
        self.assertIsNotNone(summary["observation_range"]["observed_from"])
        self.assertEqual(summary["observation_range"]["observed_from"], summary["observation_range"]["observed_to"])

        isolated = self.repository.summarize_profile_knowledge_use("user-2")
        self.assertEqual(isolated["knowledge_use_count"], 1)
        self.assertEqual(isolated["reliable_use_count"], 1)

    def test_unreliable_knowledge_use_does_not_create_an_observation_range(self) -> None:
        self.repository.record_knowledge_use(
            owner_id="user-1", mode="hybrid", candidate_count=2, ranked_count=1,
            source_count=1, citation_count=0, answerable=True,
        )

        summary = self.repository.summarize_profile_knowledge_use("user-1")
        self.assertEqual(summary["knowledge_use_count"], 1)
        self.assertEqual(summary["reliable_use_count"], 0)
        self.assertEqual(summary["observation_range"], {"observed_from": None, "observed_to": None})

if __name__ == "__main__":
    unittest.main()
