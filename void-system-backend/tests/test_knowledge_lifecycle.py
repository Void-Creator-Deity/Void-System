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

    def test_ingestion_lifecycle_completes_only_through_its_worker_lease(self) -> None:
        started = self.repository.start_ingestion(
            document_id="doc-1",
            owner_id="user-1",
            content_fingerprint="fingerprint",
            source_size=42,
            index_version="test-index-v1",
        )

        self.assertFalse(started["duplicate"])
        claimed = self.repository.claim_next("worker-one")
        self.assertIsNotNone(claimed)
        self.assertTrue(
            self.repository.complete(
                started["job_id"],
                "worker-one",
                claimed["lease_token"],
                chunk_count=3,
                index_version="test-index-v1",
            )
        )
        self.assertFalse(
            self.repository.complete(
                started["job_id"],
                "worker-two",
                claimed["lease_token"],
                chunk_count=99,
            )
        )
        self.assertIsNone(self.repository.get_job("user-2", started["job_id"]))

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

    def test_claim_is_private_and_public_reads_are_owner_scoped(self) -> None:
        started = self.repository.start_ingestion(
            document_id="doc-private",
            owner_id="user-1",
            content_fingerprint="private-source",
            source_size=24,
            index_version="test-index-v1",
        )

        self.assertIsNone(self.repository.get_job("user-2", started["job_id"]))
        claimed = self.repository.claim_next("worker-one")
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["job_id"], started["job_id"])
        self.assertTrue(claimed["lease_token"])
        self.assertEqual(claimed["worker_id"], "worker-one")

        public_job = self.repository.get_job("user-1", started["job_id"])
        self.assertEqual(public_job["status"], "processing")
        self.assertNotIn("lease_token", public_job)
        self.assertNotIn("lease_token", self.repository.list_recent_jobs("user-1")[0])

    def test_cancel_handles_queued_and_active_jobs_without_cross_owner_access(self) -> None:
        queued = self.repository.start_ingestion(
            document_id="doc-queued",
            owner_id="user-1",
            content_fingerprint="queued-source",
            source_size=1,
            index_version="test-index-v1",
        )
        cancelled = self.repository.cancel("user-1", queued["job_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["progress"], 100)
        self.assertIsNone(self.repository.claim_next("worker-one"))

        active = self.repository.start_ingestion(
            document_id="doc-active",
            owner_id="user-1",
            content_fingerprint="active-source",
            source_size=1,
            index_version="test-index-v1",
        )
        claimed = self.repository.claim_next("worker-one")
        self.assertEqual(claimed["job_id"], active["job_id"])
        self.assertIsNone(self.repository.cancel("user-2", active["job_id"]))
        cancelling = self.repository.cancel("user-1", active["job_id"])
        self.assertEqual(cancelling["status"], "cancelling")
        self.assertTrue(
            self.repository.is_cancel_requested(
                active["job_id"], "worker-one", claimed["lease_token"]
            )
        )
        self.assertTrue(
            self.repository.mark_cancelled(
                active["job_id"], "worker-one", claimed["lease_token"]
            )
        )
        self.assertEqual(self.repository.get_job("user-1", active["job_id"])["status"], "cancelled")

    def test_retry_preserves_terminal_history_and_reuses_immutable_version(self) -> None:
        started = self.repository.start_ingestion(
            document_id="doc-retry",
            owner_id="user-1",
            content_fingerprint="retry-source",
            source_size=9,
            index_version="test-index-v1",
            job_type="rebuild",
            force=True,
        )
        claimed = self.repository.claim_next("worker-one")
        self.assertTrue(
            self.repository.fail(
                started["job_id"], "worker-one", claimed["lease_token"], "Temporary parser failure"
            )
        )

        retried = self.repository.retry("user-1", started["job_id"])
        original = self.repository.get_job("user-1", started["job_id"])
        self.assertNotEqual(retried["job_id"], started["job_id"])
        self.assertEqual(retried["version_id"], original["version_id"])
        self.assertEqual(retried["status"], "queued")
        self.assertEqual(retried["job_type"], "rebuild")
        self.assertEqual(original["status"], "failed")
        self.assertEqual(original["error_message"], "Temporary parser failure")

    def test_only_current_lease_can_publish_terminal_result(self) -> None:
        started = self.repository.start_ingestion(
            document_id="doc-lease",
            owner_id="user-1",
            content_fingerprint="lease-source",
            source_size=3,
            index_version="test-index-v1",
        )
        claimed = self.repository.claim_next("worker-one")
        self.assertFalse(
            self.repository.complete(
                started["job_id"],
                "worker-one",
                "wrong-token",
                result={"success": True},
                chunk_count=1,
                index_version="test-index-v1",
            )
        )
        self.assertEqual(self.repository.get_job("user-1", started["job_id"])["status"], "processing")
        self.assertTrue(
            self.repository.complete(
                started["job_id"],
                "worker-one",
                claimed["lease_token"],
                result={"success": True, "document_id": "doc-lease"},
                chunk_count=1,
                index_version="test-index-v1",
            )
        )
        completed = self.repository.get_job("user-1", started["job_id"])
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["result"], {"success": True, "document_id": "doc-lease"})
        self.assertNotIn("lease_token", completed)

    def test_restart_recovery_requeues_abandoned_processing_work(self) -> None:
        started = self.repository.start_ingestion(
            document_id="doc-recover",
            owner_id="user-1",
            content_fingerprint="recovery-source",
            source_size=3,
            index_version="test-index-v1",
        )
        claimed = self.repository.claim_next("previous-worker")
        self.assertEqual(claimed["status"], "processing")

        self.assertEqual(self.repository.recover_interrupted_jobs(), 1)
        recovered = self.repository.get_job("user-1", started["job_id"])
        self.assertEqual(recovered["status"], "queued")
        self.assertEqual(recovered["progress"], 0)
        self.assertIsNone(recovered["worker_id"])


if __name__ == "__main__":
    unittest.main()
