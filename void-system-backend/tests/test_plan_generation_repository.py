"""Persistence behavior for durable plan-generation jobs."""
from pathlib import Path
import tempfile
import unittest

from adapters.sqlite.plan_generation_repository import SQLitePlanGenerationRepository
from modules.planning.generation import PlanGenerationService, PlanGenerationWorker
from database import Database


class PlanGenerationRepositoryTests(unittest.TestCase):
    """Verify durable queue ownership, restart recovery, cancellation, and owner isolation."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "plan-generation.db")
        connection = self.database.get_connection()
        try:
            connection.executemany(
                "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
                [("user-1", "planner", "unused"), ("user-2", "other", "unused")],
            )
            connection.commit()
        finally:
            connection.close()
        self.repository = SQLitePlanGenerationRepository(self.database.get_connection)

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def create_job(self) -> dict:
        return self.repository.create(
            "user-1",
            {
                "topic": "Publish the refreshed planner",
                "execution_mode": "assisted",
                "max_steps": 6,
                "advisor_prefs": {"detail": "focused"},
            },
        )

    def test_cancelled_generation_cannot_be_completed_later(self) -> None:
        job = self.create_job()
        claimed = self.repository.claim("user-1", job["generation_id"], worker_id="worker-a")
        self.assertIsNotNone(claimed)
        cancelled = self.repository.cancel("user-1", job["generation_id"])

        self.assertEqual(cancelled["status"], "generating")
        self.assertEqual(cancelled["stage"], "cancelling")
        self.assertTrue(cancelled["cancel_requested"])
        self.assertFalse(self.repository.complete(
            job["generation_id"], "worker-a", claimed["lease_token"], {"goal": {}}
        ))
        self.assertEqual(self.repository.get("user-1", job["generation_id"])["status"], "cancelled")

    def test_restart_requeues_interrupted_job_and_preserves_queued_job(self) -> None:
        interrupted = self.create_job()
        queued = self.create_job()
        self.assertIsNotNone(self.repository.claim("user-1", interrupted["generation_id"]))

        self.assertEqual(self.repository.recover_interrupted_jobs(), 1)
        recovered = self.repository.get("user-1", interrupted["generation_id"])
        self.assertEqual(recovered["status"], "queued")
        self.assertEqual(recovered["stage"], "queued")
        self.assertEqual(recovered["progress"], 0)
        self.assertEqual(self.repository.get("user-1", queued["generation_id"])["status"], "queued")

    def test_only_one_worker_can_claim_the_same_queued_job(self) -> None:
        job = self.create_job()
        first = self.repository.claim_next("worker-a")
        second = self.repository.claim_next("worker-b")

        self.assertEqual(first["generation_id"], job["generation_id"])
        self.assertIsNone(second)
        self.assertTrue(self.repository.update_progress(
            job["generation_id"], "worker-a", first["lease_token"], "generating_steps", 50
        ))
        self.assertFalse(self.repository.update_progress(
            job["generation_id"], "worker-b", first["lease_token"], "generating_steps", 50
        ))

    def test_worker_executes_a_persisted_job_without_a_request(self) -> None:
        service = PlanGenerationService(self.repository)
        worker = PlanGenerationWorker(
            service,
            lambda job: service.execute_claimed(
                job,
                lambda snapshot, report: {
                    "goal": {"title": snapshot["topic"]},
                    "run": {"steps": []},
                    "summary": "Generated in the durable worker.",
                },
            ),
            poll_seconds=0.01,
        )
        worker.start()
        try:
            job = self.create_job()
            worker.wake()
            for _ in range(100):
                current = self.repository.get("user-1", job["generation_id"])
                if current and current["status"] == "ready":
                    break
                __import__("time").sleep(0.01)
            self.assertEqual(current["status"], "ready")
            self.assertEqual(current["result"]["goal"]["title"], job["topic"])
            self.assertTrue(current["draft_id"])
            draft = __import__("adapters.sqlite.plan_draft_repository", fromlist=["SQLitePlanDraftRepository"]).SQLitePlanDraftRepository(self.database.get_connection).get("user-1", current["draft_id"])
            self.assertEqual(draft["generation_id"], job["generation_id"])
        finally:
            worker.stop()

    def test_job_is_not_visible_to_another_user(self) -> None:
        job = self.create_job()
        self.assertIsNone(self.repository.get("user-2", job["generation_id"]))
        self.assertIsNone(self.repository.cancel("user-2", job["generation_id"]))


if __name__ == "__main__":
    unittest.main()
