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


if __name__ == "__main__":
    unittest.main()
