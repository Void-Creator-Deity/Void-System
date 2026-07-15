"""Behavior tests for durable Goal and Run execution."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from core.task_execution_contracts import TaskExecutionError
from database import Database
from modules.tasks.service import get_task_execution


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
                "mode": "agent",
                "steps": [
                    {"client_key": "plan", "title": "Plan", "kind": "agent"},
                    {
                        "client_key": "build",
                        "title": "Build",
                        "kind": "tool",
                        "depends_on": ["plan"],
                    },
                    {
                        "client_key": "test",
                        "title": "Test",
                        "kind": "tool",
                        "depends_on": ["plan"],
                    },
                    {
                        "client_key": "review",
                        "title": "Review",
                        "kind": "review",
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
            {"steps": [{"title": "Inspect", "kind": "tool"}]},
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

    def test_run_creation_is_idempotent_and_owner_scoped(self) -> None:
        goal = self.create_goal()
        values = {"idempotency_key": "launch-2026", "steps": [{"title": "Launch"}]}
        first = self.execution.create_run("user-1", goal["goal_id"], values)
        second = self.execution.create_run("user-1", goal["goal_id"], values)
        self.assertEqual(first["run_id"], second["run_id"])

        with self.assertRaises(TaskExecutionError) as context:
            self.execution.get_run("user-2", first["run_id"])
        self.assertEqual(context.exception.code, "RUN_NOT_FOUND")

    def test_agent_lease_supports_checkpoint_and_expired_reclaim(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1",
            goal["goal_id"],
            {"mode": "agent", "steps": [{"title": "Investigate", "kind": "agent"}]},
        )
        run = self.execution.start_run("user-1", run["run_id"])
        lease = self.execution.claim_agent_run(
            "user-1", run["run_id"], "worker-a", lease_seconds=60
        )
        self.assertEqual(lease["worker_id"], "worker-a")
        token = lease["lease_token"]

        with self.assertRaises(TaskExecutionError) as conflict:
            self.execution.claim_agent_run(
                "user-1", run["run_id"], "worker-b", lease_seconds=60
            )
        self.assertEqual(conflict.exception.code, "RUN_LEASE_CONFLICT")

        lease = self.execution.heartbeat_agent_run(
            "user-1",
            run["run_id"],
            token,
            checkpoint_data={"cursor": 4, "summary": "tools inspected"},
        )
        self.assertEqual(lease["checkpoint_data"]["cursor"], 4)

        connection = self.database.get_connection()
        connection.execute(
            "UPDATE task_run_leases SET expires_at = ? WHERE run_id = ?",
            ("2000-01-01T00:00:00+00:00", run["run_id"]),
        )
        connection.commit()
        connection.close()

        reclaimed = self.execution.claim_agent_run(
            "user-1", run["run_id"], "worker-b", lease_seconds=60
        )
        self.assertEqual(reclaimed["worker_id"], "worker-b")
        self.assertNotEqual(reclaimed["lease_token"], token)
        self.assertEqual(reclaimed["checkpoint_data"]["cursor"], 4)
        with self.assertRaises(TaskExecutionError) as stale:
            self.execution.heartbeat_agent_run("user-1", run["run_id"], token)
        self.assertEqual(stale.exception.code, "RUN_LEASE_INVALID")
        events = self.execution.list_events("user-1", run["run_id"])
        self.assertIn("run.lease_reclaimed", [event["event_type"] for event in events])

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
