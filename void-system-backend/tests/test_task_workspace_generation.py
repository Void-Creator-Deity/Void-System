"""Task Workspace tests for generated legacy chains through PlanningEngine."""
from pathlib import Path
import tempfile
import unittest

from core.planning_contracts import PlanResult, PlannedTask
from core.task_workspace_contracts import TaskWorkspaceError
from database import Database
from modules.tasks.service import get_task_workspace


class FakePlanner:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.requests = []

    def plan(self, request):
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("planner unavailable")
        return PlanResult(
            response="Plan ready",
            mode="workflow_chain",
            tasks=[
                PlannedTask(title="Inspect", description="Inspect the current state."),
                PlannedTask(title="Improve", description="Implement the improvement."),
            ],
        )


class TaskWorkspaceGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "workspace-generation.db")
        connection = self.database.get_connection()
        connection.execute(
            "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
            ("user-1", "planner-owner", "unused"),
        )
        connection.commit()
        connection.close()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generated_chain_uses_planning_engine_and_persists_steps(self) -> None:
        planner = FakePlanner()
        workspace = get_task_workspace(self.database, planner=planner)
        creation = workspace.create_chain(
            "user-1",
            {
                "chain_name": "Improve architecture",
                "target_goal": "Make task execution maintainable",
            },
        )
        count = workspace.generate_chain_steps(
            "user-1",
            creation.chain_id,
            "Make task execution maintainable",
            {"specialization": "Backend engineering"},
        )
        self.assertEqual(count, 2)
        self.assertEqual(len(planner.requests), 1)
        self.assertEqual(planner.requests[0].mode, "auto")
        self.assertTrue(planner.requests[0].strict)
        chain = next(
            item for item in workspace.list_chains("user-1")
            if item["chain_id"] == creation.chain_id
        )
        self.assertEqual(chain["generation_status"], "ready")
        tasks = workspace.list_tasks("user-1")["tasks"]
        self.assertEqual([item["task_name"] for item in tasks], ["Inspect", "Improve"])

    def test_generation_failure_is_recorded_by_workspace_module(self) -> None:
        workspace = get_task_workspace(self.database, planner=FakePlanner(fail=True))
        creation = workspace.create_chain(
            "user-1",
            {"chain_name": "Unavailable plan", "target_goal": "Generate work"},
        )
        with self.assertRaises(TaskWorkspaceError) as context:
            workspace.generate_chain_steps(
                "user-1", creation.chain_id, "Generate work", {}
            )
        self.assertEqual(context.exception.code, "TASK_CHAIN_GENERATION_FAILED")
        chain = next(
            item for item in workspace.list_chains("user-1")
            if item["chain_id"] == creation.chain_id
        )
        self.assertEqual(chain["generation_status"], "failed")
        self.assertTrue(chain["generation_error"])


if __name__ == "__main__":
    unittest.main()
