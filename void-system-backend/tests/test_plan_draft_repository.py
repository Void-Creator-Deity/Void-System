"""Owner, edit, and atomic-publication tests for persisted Plan Drafts."""
from pathlib import Path
import tempfile
import unittest

from adapters.sqlite.plan_draft_repository import SQLitePlanDraftRepository
from adapters.sqlite.plan_generation_repository import SQLitePlanGenerationRepository
from database import Database
from errors import VoidSystemException
from modules.planning.drafts import PlanDraftService
from modules.tasks.service import get_task_execution


class PlanDraftRepositoryTests(unittest.TestCase):
    """Prove drafts replace browser-local history without creating partial execution records."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "plan-drafts.db")
        connection = self.database.get_connection()
        try:
            connection.executemany(
                "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
                [("user-1", "owner", "unused"), ("user-2", "other", "unused")],
            )
            connection.commit()
        finally:
            connection.close()
        self.repository = SQLitePlanDraftRepository(self.database.get_connection)
        self.generation_repository = SQLitePlanGenerationRepository(self.database.get_connection)
        self.service = PlanDraftService(self.repository, get_task_execution(self.database))

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    @staticmethod
    def valid_payload() -> dict:
        return {
            "goal": {
                "title": "完成持久化方案草稿",
                "description": "让计划能在刷新后继续编辑和发布。",
                "desired_outcome": "可恢复的计划发布闭环",
                "priority": "high",
            },
            "run": {
                "title": "实现方案草稿发布",
                "objective": "发布并开始第一轮行动",
                "mode": "assisted",
                "steps": [
                    {
                        "client_key": "model",
                        "title": "建立草稿模型",
                        "description": "增加持久化表和读取接口。",
                        "kind": "manual",
                        "max_attempts": 1,
                        "completion_criteria": {},
                        "input_data": {},
                        "depends_on": [],
                    },
                    {
                        "client_key": "publish",
                        "title": "原子发布",
                        "description": "将草稿转为目标和行动。",
                        "kind": "manual",
                        "max_attempts": 1,
                        "completion_criteria": {},
                        "input_data": {},
                        "depends_on": ["model"],
                    },
                ],
            },
            "summary": "先把草稿持久化，再开始行动。",
            "estimated_duration": "1 天",
            "meta": {"needs_review": True},
        }

    def create_draft(self) -> dict:
        job = self.generation_repository.create(
            "user-1",
            {
                "topic": "Persist Plan Draft",
                "execution_mode": "assisted",
                "max_steps": 2,
                "advisor_prefs": {},
            },
        )
        return self.repository.create_from_generation("user-1", job["generation_id"], self.valid_payload())

    def test_drafts_are_owner_scoped_and_generation_is_unique(self) -> None:
        draft = self.create_draft()
        same = self.repository.create_from_generation("user-1", draft["generation_id"], self.valid_payload())

        self.assertEqual(draft["draft_id"], same["draft_id"])
        self.assertIsNone(self.repository.get("user-2", draft["draft_id"]))
        self.assertEqual([draft["draft_id"]], [item["draft_id"] for item in self.service.list_recent("user-1")])

    def test_edit_requires_current_version_and_normalizes_payload(self) -> None:
        draft = self.create_draft()
        edited = self.valid_payload()
        edited["goal"]["title"] = "完成持久化方案草稿（已调整）"
        saved = self.service.update("user-1", draft["draft_id"], edited, draft["version"])

        self.assertEqual(saved["version"], 2)
        self.assertEqual(saved["payload"]["goal"]["title"], edited["goal"]["title"])
        with self.assertRaises(VoidSystemException) as stale:
            self.service.update("user-1", draft["draft_id"], edited, draft["version"])
        self.assertEqual(stale.exception.error_code, "PLAN_DRAFT_VERSION_CONFLICT")

    def test_publish_is_atomic_idempotent_and_starts_only_ready_steps(self) -> None:
        draft = self.create_draft()
        published = self.service.publish("user-1", draft["draft_id"], "retry-key-1")
        retried = self.service.publish("user-1", draft["draft_id"], "retry-key-1")

        self.assertEqual(published["status"], "published")
        self.assertEqual(published["published_goal_id"], retried["published_goal_id"])
        self.assertEqual(published["published_run_id"], retried["published_run_id"])
        run = get_task_execution(self.database).get_run("user-1", published["published_run_id"])
        self.assertEqual(run["status"], "running")
        statuses = {step["client_key"]: step["status"] for step in run["steps"]}
        self.assertEqual(statuses, {"model": "ready", "publish": "pending"})
        connection = self.database.get_connection()
        try:
            goal_count = connection.execute("SELECT COUNT(*) FROM task_goals WHERE user_id = 'user-1'").fetchone()[0]
            run_count = connection.execute("SELECT COUNT(*) FROM task_runs WHERE user_id = 'user-1'").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual((goal_count, run_count), (1, 1))

    def test_publish_rejects_a_second_key_without_creating_another_run(self) -> None:
        draft = self.create_draft()
        self.service.publish("user-1", draft["draft_id"], "retry-key-1")

        with self.assertRaises(VoidSystemException) as conflict:
            self.service.publish("user-1", draft["draft_id"], "retry-key-2")
        self.assertEqual(conflict.exception.error_code, "PLAN_DRAFT_ALREADY_PUBLISHED")


if __name__ == "__main__":
    unittest.main()
