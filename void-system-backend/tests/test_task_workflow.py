from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.planning_contracts import EvaluationResult
from core.task_contracts import RewardGrant, TaskWorkflowError
from database import Database
from modules.tasks.workflow import TaskWorkflow


class FakeTaskRepository:
    def __init__(self) -> None:
        self.tasks: List[Dict[str, Any]] = [
            {
                "task_id": "task-1",
                "task_name": "实现模块",
                "status": "pending",
                "prerequisites": [],
                "reward_coins": 20,
                "attribute_points": 5,
                "related_attrs": {"focus": 1, "craft": 3},
            }
        ]
        self.attributes = [
            {"attr_id": "focus", "attr_value": 10, "max_value": 100},
            {"attr_id": "craft", "attr_value": 20, "max_value": 100},
        ]
        self.settlements: List[RewardGrant] = []
        self.evaluations: List[Dict[str, Any]] = []

    def get_task(self, user_id: str, task_id: str):
        return next((task for task in self.tasks if task["task_id"] == task_id), None)

    def list_tasks(self, user_id: str):
        return self.tasks

    def list_attributes(self, user_id: str):
        return self.attributes

    def update_status(self, user_id: str, task_id: str, status: str) -> bool:
        task = self.get_task(user_id, task_id)
        if not task:
            return False
        task["status"] = status
        return True

    def submit_proof(self, user_id: str, task_id: str, proof: Dict[str, Any]) -> bool:
        task = self.get_task(user_id, task_id)
        if not task:
            return False
        task["proof_data"] = proof
        task["status"] = "pending_evaluation"
        return True

    def update_evaluation(
        self, user_id: str, task_id: str, *,
        self_evaluation: Optional[Dict[str, Any]] = None,
        ai_suggestion: Optional[Dict[str, Any]] = None,
    ) -> bool:
        self.evaluations.append({
            "self_evaluation": self_evaluation,
            "ai_suggestion": ai_suggestion,
        })
        return True

    def settle_completion(
        self, user_id: str, task_id: str, reward: RewardGrant, *,
        ai_suggestion: Optional[Dict[str, Any]] = None,
    ) -> bool:
        task = self.get_task(user_id, task_id)
        if not task or task["status"] == "completed":
            return False
        task["status"] = "completed"
        self.settlements.append(reward)
        if ai_suggestion is not None:
            self.evaluations.append({"ai_suggestion": ai_suggestion})
        return True


class PassingEvaluator:
    def evaluate(self, request):
        return EvaluationResult(
            status="pass",
            feedback="证据完整",
            score=90,
            suggested_rewards={"coins": 30, "focus": 2},
            raw={},
        )


class TaskWorkflowTests(unittest.TestCase):
    def test_completion_allocates_weighted_rewards_once(self) -> None:
        repository = FakeTaskRepository()
        workflow = TaskWorkflow(repository)

        first = workflow.change_status("user-1", "task-1", "completed")
        second = workflow.change_status("user-1", "task-1", "completed")

        self.assertTrue(first.reward_granted)
        self.assertFalse(second.reward_granted)
        self.assertEqual(len(repository.settlements), 1)
        self.assertEqual(repository.settlements[0].attribute_increments, {"focus": 1, "craft": 4})

    def test_prerequisites_are_enforced_consistently(self) -> None:
        repository = FakeTaskRepository()
        repository.tasks[0]["prerequisites"] = ["missing-task"]
        workflow = TaskWorkflow(repository)

        with self.assertRaises(TaskWorkflowError) as context:
            workflow.submit_proof("user-1", "task-1", {"text": "done"})

        self.assertEqual(context.exception.code, "PREREQUISITES_NOT_MET")

    def test_ai_evaluation_task_cannot_bypass_evaluator(self) -> None:
        repository = FakeTaskRepository()
        repository.tasks[0]["completion_type"] = "ai_eval"

        with self.assertRaises(TaskWorkflowError) as context:
            TaskWorkflow(repository).change_status("user-1", "task-1", "completed")

        self.assertEqual(context.exception.code, "TASK_EVALUATION_REQUIRED")
        self.assertEqual(repository.settlements, [])

    def test_proof_submission_can_complete_after_evidence_is_saved(self) -> None:
        repository = FakeTaskRepository()
        repository.tasks[0]["completion_type"] = "submission"
        workflow = TaskWorkflow(repository)

        workflow.submit_proof("user-1", "task-1", {"text": "done"})
        completion = workflow.change_status("user-1", "task-1", "completed")

        self.assertTrue(completion.reward_granted)
        self.assertEqual(repository.tasks[0]["status"], "completed")

    def test_ai_pass_uses_suggested_rewards_and_settles(self) -> None:
        repository = FakeTaskRepository()
        outcome = TaskWorkflow(repository, PassingEvaluator()).evaluate_submission(
            "user-1", "task-1", "完成记录", []
        )

        self.assertEqual(outcome.status, "pass")
        self.assertTrue(outcome.reward_granted)
        self.assertEqual(repository.settlements[0].coins, 30)
        self.assertEqual(repository.settlements[0].attribute_increments, {"focus": 2})


class SQLiteSettlementTests(unittest.TestCase):
    def test_settlement_is_atomic_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(str(Path(temp_dir) / "test.db"))
            conn = database.get_connection()
            conn.execute(
                "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
                ("user-1", "tester", "unused"),
            )
            conn.execute(
                """INSERT INTO tasks
                   (task_id, user_id, task_name, status, reward_coins, attribute_points)
                   VALUES (?, ?, ?, 'pending', 20, 4)""",
                ("task-1", "user-1", "Test task"),
            )
            conn.execute(
                """INSERT INTO attributes
                   (attr_id, user_id, attr_name, attr_value, max_value)
                   VALUES (?, ?, ?, ?, ?)""",
                ("focus", "user-1", "Focus", 98, 100),
            )
            conn.commit()
            conn.close()

            first = database.settle_task_completion(
                "task-1", "user-1", 20, 10, {"focus": 4}, "task_task-1_complete"
            )
            second = database.settle_task_completion(
                "task-1", "user-1", 20, 10, {"focus": 4}, "task_task-1_complete"
            )

            self.assertTrue(first)
            self.assertFalse(second)
            conn = database.get_connection()
            settlement = conn.execute(
                """SELECT run_id, step_id FROM task_reward_settlements
                   WHERE task_id = 'task-1'"""
            ).fetchone()
            self.assertIsNotNone(settlement["run_id"])
            self.assertIsNotNone(settlement["step_id"])
            self.assertEqual(conn.execute(
                """SELECT COUNT(*) FROM task_events
                   WHERE run_id = ? AND step_id = ? AND event_type = 'reward.settled'""",
                (settlement["run_id"], settlement["step_id"]),
            ).fetchone()[0], 1)
            self.assertEqual(conn.execute(
                "SELECT SUM(amount) FROM coins WHERE user_id = 'user-1'"
            ).fetchone()[0], 20)
            self.assertEqual(conn.execute(
                "SELECT experience FROM users WHERE user_id = 'user-1'"
            ).fetchone()[0], 10)
            self.assertEqual(conn.execute(
                "SELECT attr_value FROM attributes WHERE attr_id = 'focus'"
            ).fetchone()[0], 100)
            self.assertEqual(conn.execute(
                "SELECT status FROM tasks WHERE task_id = 'task-1'"
            ).fetchone()[0], "completed")
            conn.close()


if __name__ == "__main__":
    unittest.main()
