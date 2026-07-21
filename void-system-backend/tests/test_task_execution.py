"""Behavior tests for durable Goal and Run execution."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from adapters.sqlite.task_execution_repository import SQLiteTaskExecutionRepository
from core.planning_contracts import EvaluationResult
from core.task_execution_contracts import TaskExecutionError
from database import Database
from modules.tasks.execution import TaskExecution
from modules.tasks.service import get_task_execution


class _PassingEvaluationEngine:
    """Deterministic review double for the assisted execution contract."""

    def evaluate(self, _request):
        return EvaluationResult(
            status="pass",
            feedback="Evidence meets the completion criteria.",
            score=92,
        )


class TaskExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "execution.db")
        connection = self.database.get_connection()
        connection.execute(
            "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
            ("user-1", "runner", "unused"),
        )
        connection.execute(
            "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
            ("user-2", "other", "unused"),
        )
        connection.commit()
        connection.close()
        self.execution = get_task_execution(self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_goal(self) -> dict:
        return self.execution.create_goal(
            "user-1",
            {"title": "Release the workspace", "desired_outcome": "A verified release"},
        )

    def test_dependency_graph_unlocks_parallel_steps_and_completes_run(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1",
            goal["goal_id"],
            {
                "mode": "manual",
                "steps": [
                    {"client_key": "plan", "title": "Plan", "kind": "manual"},
                    {
                        "client_key": "build",
                        "title": "Build",
                                                "depends_on": ["plan"],
                    },
                    {
                        "client_key": "test",
                        "title": "Test",
                        "kind": "manual",
                        "depends_on": ["plan"],
                    },
                    {
                        "client_key": "review",
                        "title": "Review",
                                                "depends_on": ["build", "test"],
                    },
                ],
            },
        )
        run = self.execution.start_run("user-1", run["run_id"])
        by_key = {step["client_key"]: step for step in run["steps"]}
        self.assertEqual(by_key["plan"]["status"], "ready")
        self.assertEqual(by_key["build"]["status"], "pending")
        self.assertEqual(by_key["test"]["status"], "pending")

        run = self.execution.start_step("user-1", run["run_id"], by_key["plan"]["step_id"])
        run = self.execution.complete_step(
            "user-1",
            run["run_id"],
            by_key["plan"]["step_id"],
            output_data={"plan": "ready"},
            artifacts=[{"title": "Release plan", "kind": "document", "uri": "memory://plan"}],
        )
        by_key = {step["client_key"]: step for step in run["steps"]}
        self.assertEqual(by_key["build"]["status"], "ready")
        self.assertEqual(by_key["test"]["status"], "ready")
        self.assertEqual(by_key["review"]["status"], "pending")
        self.assertEqual(len(run["artifacts"]), 1)

        for key in ("build", "test"):
            run = self.execution.start_step("user-1", run["run_id"], by_key[key]["step_id"])
            run = self.execution.complete_step("user-1", run["run_id"], by_key[key]["step_id"])
        by_key = {step["client_key"]: step for step in run["steps"]}
        self.assertEqual(by_key["review"]["status"], "ready")
        run = self.execution.start_step("user-1", run["run_id"], by_key["review"]["step_id"])
        run = self.execution.complete_step("user-1", run["run_id"], by_key["review"]["step_id"])
        self.assertEqual(run["status"], "completed")

        event_types = [
            event["event_type"] for event in self.execution.list_events("user-1", run["run_id"])
        ]
        self.assertIn("run.created", event_types)
        self.assertIn("run.completed", event_types)
        self.assertEqual(event_types.count("step.ready"), 4)

    def test_approval_is_durable_and_required_only_once(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1",
            goal["goal_id"],
            {"steps": [{"title": "Publish", "requires_approval": True}]},
        )
        run = self.execution.start_run("user-1", run["run_id"])
        step_id = run["steps"][0]["step_id"]

        run = self.execution.start_step("user-1", run["run_id"], step_id)
        self.assertEqual(run["status"], "waiting_approval")
        self.assertEqual(run["steps"][0]["status"], "waiting_approval")
        approval_id = run["approvals"][0]["approval_id"]

        run = self.execution.resolve_approval("user-1", approval_id, "approved", "Proceed")
        self.assertEqual(run["status"], "running")
        self.assertEqual(run["steps"][0]["status"], "ready")
        run = self.execution.start_step("user-1", run["run_id"], step_id)
        self.assertEqual(run["steps"][0]["status"], "running")

    def test_failed_step_can_retry_until_attempt_limit(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1",
            goal["goal_id"],
            {"steps": [{"title": "Deploy", "max_attempts": 2}]},
        )
        run = self.execution.start_run("user-1", run["run_id"])
        step_id = run["steps"][0]["step_id"]
        run = self.execution.start_step("user-1", run["run_id"], step_id)
        run = self.execution.fail_step("user-1", run["run_id"], step_id, "Network unavailable")
        run = self.execution.retry_step("user-1", run["run_id"], step_id)
        run = self.execution.start_step("user-1", run["run_id"], step_id)
        run = self.execution.fail_step("user-1", run["run_id"], step_id, "Still unavailable")

        with self.assertRaises(TaskExecutionError) as context:
            self.execution.retry_step("user-1", run["run_id"], step_id)
        self.assertEqual(context.exception.code, "STEP_ATTEMPTS_EXHAUSTED")

    def test_pause_resume_and_action_history_use_the_same_run(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1",
            goal["goal_id"],
            {"steps": [{"title": "Inspect", "kind": "manual"}]},
        )
        run = self.execution.start_run("user-1", run["run_id"])
        run = self.execution.pause_run("user-1", run["run_id"])
        self.assertEqual(run["status"], "paused")
        run = self.execution.resume_run("user-1", run["run_id"])
        step_id = run["steps"][0]["step_id"]
        run = self.execution.start_step("user-1", run["run_id"], step_id)
        action = self.execution.start_action(
            "user-1",
            run["run_id"],
            step_id,
            {
                "action_type": "tool",
                "tool_name": "test-runner",
                "idempotency_key": "tests-1",
            },
        )
        duplicate = self.execution.start_action(
            "user-1",
            run["run_id"],
            step_id,
            {
                "action_type": "tool",
                "tool_name": "test-runner",
                "idempotency_key": "tests-1",
            },
        )
        self.assertEqual(action["action_id"], duplicate["action_id"])
        self.execution.complete_action(
            "user-1",
            run["run_id"],
            step_id,
            action["action_id"],
            status="completed",
            output_data={"passed": 12},
        )
        events = self.execution.list_events("user-1", run["run_id"])
        self.assertIn("run.paused", [event["event_type"] for event in events])
        self.assertIn("run.resumed", [event["event_type"] for event in events])
        self.assertIn("action.completed", [event["event_type"] for event in events])

    def test_profile_behavior_summary_uses_only_aggregate_goal_and_approval_signals(self) -> None:
        first_goal = self.create_goal()
        second_goal = self.execution.create_goal(
            "user-1", {"title": "Improve the workspace", "desired_outcome": "A clearer flow"}
        )
        self.execution.update_goal(
            "user-1", first_goal["goal_id"], {"desired_outcome": "A verified public release"}
        )
        self.execution.update_goal(
            "user-1", first_goal["goal_id"], {"priority": "high"}
        )
        self.execution.update_goal(
            "user-1", second_goal["goal_id"], {"title": "Improve the daily workspace"}
        )
        for index, decision in enumerate(("approved", "approved", "rejected")):
            goal = first_goal if index < 2 else second_goal
            run = self.execution.create_run(
                "user-1",
                goal["goal_id"],
                {"title": f"Approval {index}", "steps": [{"title": "Review", "requires_approval": True}]},
            )
            run = self.execution.start_run("user-1", run["run_id"])
            step_id = run["steps"][0]["step_id"]
            run = self.execution.start_step("user-1", run["run_id"], step_id)
            self.execution.resolve_approval("user-1", run["approvals"][0]["approval_id"], decision)

        self.execution.update_goal("user-1", first_goal["goal_id"], {"status": "completed"})

        summary = self.execution.summarize_profile_behavior("user-1")
        self.assertEqual(summary["approval_count"], 3)
        self.assertEqual(summary["approved_approval_count"], 2)
        self.assertEqual(summary["rejected_approval_count"], 1)
        self.assertEqual(summary["goal_plan_refinement_count"], 3)
        self.assertEqual(summary["refined_goal_count"], 2)
        self.assertEqual(summary["goal_change_count"], 4)
    def test_profile_behavior_summary_has_safe_observation_ranges_and_ignores_pending_approvals(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1",
            goal["goal_id"],
            {"steps": [{"title": "Needs a decision", "requires_approval": True}]},
        )
        run = self.execution.start_run("user-1", run["run_id"])
        self.execution.start_step("user-1", run["run_id"], run["steps"][0]["step_id"])

        summary = self.execution.summarize_profile_behavior("user-1")

        self.assertEqual(summary["approval_count"], 0)
        self.assertEqual(summary["approved_approval_count"], 0)
        self.assertEqual(summary["observation_ranges"]["approvals"], {
            "observed_from": None,
            "observed_to": None,
        })
        self.assertIsNotNone(summary["observation_ranges"]["runs"]["observed_from"])
        self.assertIsNotNone(summary["observation_ranges"]["runs"]["observed_to"])
        self.assertNotIn("Release the workspace", str(summary))
        self.assertNotIn("Needs a decision", str(summary))

    def test_run_creation_is_idempotent_and_owner_scoped(self) -> None:
        goal = self.create_goal()
        values = {"idempotency_key": "launch-2026", "steps": [{"title": "Launch"}]}
        first = self.execution.create_run("user-1", goal["goal_id"], values)
        second = self.execution.create_run("user-1", goal["goal_id"], values)
        self.assertEqual(first["run_id"], second["run_id"])

        with self.assertRaises(TaskExecutionError) as context:
            self.execution.get_run("user-2", first["run_id"])
        self.assertEqual(context.exception.code, "RUN_NOT_FOUND")

    def test_assisted_step_requires_evidence_then_persists_confirmed_review(self) -> None:
        goal = self.create_goal()
        execution = TaskExecution(
            SQLiteTaskExecutionRepository(self.database.get_connection),
            evaluation_engine=_PassingEvaluationEngine(),
        )
        run = execution.create_run(
            "user-1",
            goal["goal_id"],
            {"mode": "assisted", "steps": [{"title": "Investigate"}]},
        )
        run = execution.start_run("user-1", run["run_id"])
        step_id = run["steps"][0]["step_id"]
        execution.start_step("user-1", run["run_id"], step_id)

        with self.assertRaises(TaskExecutionError) as context:
            execution.complete_step("user-1", run["run_id"], step_id)
        self.assertEqual(context.exception.code, "ASSISTED_REVIEW_REQUIRED")

        reviewed = execution.review_assisted_step(
            "user-1",
            run["run_id"],
            step_id,
            {"submission": "Inspected the module boundary and recorded the result."},
        )
        self.assertEqual(reviewed["status"], "completed")
        self.assertEqual(reviewed["steps"][0]["status"], "completed")
        self.assertEqual(reviewed["actions"][0]["status"], "confirmed")
        self.assertEqual(
            reviewed["actions"][0]["input_data"]["submission"],
            "Inspected the module boundary and recorded the result.",
        )
        event_types = [event["event_type"] for event in execution.list_events("user-1", run["run_id"])]
        self.assertIn("step.completed_after_review", event_types)

    def test_manual_completion_settles_published_growth_points_once(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1",
            goal["goal_id"],
            {
                "steps": [
                    {
                        "title": "Publish the verified release",
                        "reward_spec": {"growth_points": 17},
                    }
                ]
            },
        )
        run = self.execution.start_run("user-1", run["run_id"])
        step_id = run["steps"][0]["step_id"]
        self.execution.start_step("user-1", run["run_id"], step_id)
        completed = self.execution.complete_step("user-1", run["run_id"], step_id)

        self.assertEqual(completed["steps"][0]["status"], "completed")
        review = self.execution.get_run_review("user-1", run["run_id"])
        self.assertEqual(review["rewards"]["totals"], {"growth_points": 17, "settlements": 1})
        self.assertEqual(review["rewards"]["items"][0]["growth_points"], 17)

        events = self.execution.list_events("user-1", run["run_id"])
        completion_event = next(event for event in events if event["event_type"] == "step.completed")
        self.assertEqual(completion_event["payload"]["reward_settlement"]["growth_points"], 17)

        connection = self.database.get_connection()
        try:
            settlements = connection.execute(
                "SELECT COUNT(*) FROM task_reward_settlements WHERE user_id = ? AND step_id = ?",
                ("user-1", step_id),
            ).fetchone()[0]
            ledger_entries = connection.execute(
                "SELECT amount, source FROM growth_point_ledger WHERE user_id = ?", ("user-1",)
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(settlements, 1)
        self.assertEqual([(row[0], row[1]) for row in ledger_entries], [(17, f"task_step:{step_id}")])

        with self.assertRaises(TaskExecutionError) as context:
            self.execution.complete_step("user-1", run["run_id"], step_id)
        self.assertEqual(context.exception.code, "RUN_STATUS_CONFLICT")
        self.assertEqual(self.execution.get_run_review("user-1", run["run_id"])["rewards"]["totals"]["growth_points"], 17)

    def test_assisted_approval_settles_growth_points_but_unavailable_review_does_not(self) -> None:
        goal = self.create_goal()
        approved_execution = TaskExecution(
            SQLiteTaskExecutionRepository(self.database.get_connection),
            evaluation_engine=_PassingEvaluationEngine(),
        )
        approved = approved_execution.create_run(
            "user-1",
            goal["goal_id"],
            {
                "mode": "assisted",
                "steps": [{"title": "Review evidence", "reward_spec": {"growth_points": 23}}],
            },
        )
        approved = approved_execution.start_run("user-1", approved["run_id"])
        approved_step_id = approved["steps"][0]["step_id"]
        approved_execution.start_step("user-1", approved["run_id"], approved_step_id)
        approved_execution.review_assisted_step(
            "user-1", approved["run_id"], approved_step_id, {"submission": "Evidence submitted."}
        )
        self.assertEqual(
            approved_execution.get_run_review("user-1", approved["run_id"])["rewards"]["totals"],
            {"growth_points": 23, "settlements": 1},
        )

        unavailable_execution = TaskExecution(SQLiteTaskExecutionRepository(self.database.get_connection))
        unavailable = unavailable_execution.create_run(
            "user-1",
            goal["goal_id"],
            {
                "mode": "assisted",
                "steps": [{"title": "Wait for review", "reward_spec": {"growth_points": 29}}],
            },
        )
        unavailable = unavailable_execution.start_run("user-1", unavailable["run_id"])
        unavailable_step_id = unavailable["steps"][0]["step_id"]
        unavailable_execution.start_step("user-1", unavailable["run_id"], unavailable_step_id)
        unavailable_result = unavailable_execution.review_assisted_step(
            "user-1", unavailable["run_id"], unavailable_step_id, {"submission": "Saved evidence."}
        )
        self.assertEqual(unavailable_result["steps"][0]["status"], "running")
        self.assertEqual(
            unavailable_execution.get_run_review("user-1", unavailable["run_id"])["rewards"]["totals"],
            {"growth_points": 0, "settlements": 0},
        )

    def test_invalid_reward_specifications_are_rejected_before_persistence(self) -> None:
        goal = self.create_goal()
        invalid_specs = [
            {"growth_points": -1},
            {"growth_points": 1001},
            {"growth_points": True},
            {"growth_points": "10"},
            {"growth_points": 1, "attribute_points": 2},
            ["not-an-object"],
        ]
        for reward_spec in invalid_specs:
            with self.subTest(reward_spec=reward_spec):
                with self.assertRaises(TaskExecutionError) as context:
                    self.execution.create_run(
                        "user-1",
                        goal["goal_id"],
                        {"steps": [{"title": "Validate reward", "reward_spec": reward_spec}]},
                    )
                self.assertEqual(context.exception.code, "STEP_REWARD_INVALID")

    def test_reward_ledger_failure_rolls_back_completed_step_and_settlement(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1",
            goal["goal_id"],
            {"steps": [{"title": "Atomic reward", "reward_spec": {"growth_points": 31}}]},
        )
        run = self.execution.start_run("user-1", run["run_id"])
        step_id = run["steps"][0]["step_id"]
        self.execution.start_step("user-1", run["run_id"], step_id)
        connection = self.database.get_connection()
        try:
            connection.execute(
                """CREATE TRIGGER fail_growth_ledger_insert
                   BEFORE INSERT ON growth_point_ledger
                   WHEN NEW.source LIKE 'task_step:%'
                   BEGIN
                       SELECT RAISE(ABORT, 'growth ledger unavailable');
                   END"""
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(sqlite3.IntegrityError):
            self.execution.complete_step("user-1", run["run_id"], step_id)

        unchanged = self.execution.get_run("user-1", run["run_id"])
        self.assertEqual(unchanged["steps"][0]["status"], "running")
        connection = self.database.get_connection()
        try:
            settlement_count = connection.execute(
                "SELECT COUNT(*) FROM task_reward_settlements WHERE step_id = ?", (step_id,)
            ).fetchone()[0]
            ledger_count = connection.execute(
                "SELECT COUNT(*) FROM growth_point_ledger WHERE source = ?", (f"task_step:{step_id}",)
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(settlement_count, 0)
        self.assertEqual(ledger_count, 0)

    def test_state_transition_rolls_back_when_event_append_fails(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1", goal["goal_id"], {"steps": [{"title": "Atomic start"}]}
        )
        connection = self.database.get_connection()
        connection.execute(
            """CREATE TRIGGER fail_run_started_event
               BEFORE INSERT ON task_events
               WHEN NEW.event_type = 'run.started'
               BEGIN
                   SELECT RAISE(ABORT, 'event append failed');
               END"""
        )
        connection.commit()
        connection.close()

        with self.assertRaises(sqlite3.IntegrityError):
            self.execution.start_run("user-1", run["run_id"])

        unchanged = self.execution.get_run("user-1", run["run_id"])
        self.assertEqual(unchanged["status"], "queued")
        self.assertEqual(unchanged["steps"][0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
