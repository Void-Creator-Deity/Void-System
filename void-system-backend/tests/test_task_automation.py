"""Behavior tests for Trigger-to-Run automation and durable Run commands."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from core.task_automation_contracts import TaskAutomationError
from database import Database
from modules.tasks.service import get_task_automation, get_task_execution


class TaskAutomationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "automation.db")
        connection = self.database.get_connection()
        connection.execute(
            "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
            ("user-1", "automation-owner", "unused"),
        )
        connection.execute(
            "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
            ("user-2", "other-owner", "unused"),
        )
        connection.commit()
        connection.close()
        self.execution = get_task_execution(self.database)
        self.automation = get_task_automation(self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_goal(self) -> dict:
        return self.execution.create_goal(
            "user-1", {"title": "Publish weekly review"}
        )

    def create_trigger(self) -> dict:
        goal = self.create_goal()
        return self.automation.create_trigger(
            "user-1",
            {
                "goal_id": goal["goal_id"],
                "name": "Weekly review ready",
                "trigger_type": "event",
                "configuration": {"event_type": "review.ready"},
                "run_template": {
                    "mode": "agent",
                    "steps": [
                        {
                            "client_key": "collect",
                            "title": "Collect evidence",
                            "kind": "agent",
                        },
                        {
                            "client_key": "publish",
                            "title": "Publish review",
                            "kind": "review",
                            "depends_on": ["collect"],
                        },
                    ],
                },
            },
        )

    def test_trigger_creates_one_canonical_run_for_each_source(self) -> None:
        trigger = self.create_trigger()
        first = self.automation.fire_trigger(
            "user-1", trigger["trigger_id"], "review:2026-28", {"week": 28}
        )
        second = self.automation.fire_trigger(
            "user-1", trigger["trigger_id"], "review:2026-28", {"week": 28}
        )
        self.assertEqual(first["run"]["run_id"], second["run"]["run_id"])
        self.assertEqual(first["firing"]["firing_id"], second["firing"]["firing_id"])
        self.assertEqual(
            [step["client_key"] for step in first["run"]["steps"]],
            ["collect", "publish"],
        )
        self.assertEqual(
            [item["client_key"] for item in first["run"]["steps"][1]["depends_on"]],
            ["collect"],
        )
        events = self.execution.list_events("user-1", first["run"]["run_id"])
        self.assertEqual(
            [event["event_type"] for event in events].count("trigger.fired"), 1
        )

    def test_long_source_key_uses_a_bounded_run_idempotency_key(self) -> None:
        trigger = self.create_trigger()
        source_key = "source:" + ("x" * 193)
        fired = self.automation.fire_trigger(
            "user-1", trigger["trigger_id"], source_key
        )
        replay = self.automation.fire_trigger(
            "user-1", trigger["trigger_id"], source_key
        )
        self.assertEqual(fired["run"]["run_id"], replay["run"]["run_id"])
        self.assertLessEqual(len(fired["run"]["idempotency_key"]), 200)

    def test_paused_trigger_rejects_new_firing_but_replays_existing_result(self) -> None:
        trigger = self.create_trigger()
        fired = self.automation.fire_trigger(
            "user-1", trigger["trigger_id"], "existing"
        )
        self.automation.pause_trigger("user-1", trigger["trigger_id"])
        replay = self.automation.fire_trigger(
            "user-1", trigger["trigger_id"], "existing"
        )
        self.assertEqual(fired["run"]["run_id"], replay["run"]["run_id"])
        with self.assertRaises(TaskAutomationError) as context:
            self.automation.fire_trigger(
                "user-1", trigger["trigger_id"], "new-source"
            )
        self.assertEqual(context.exception.code, "TRIGGER_NOT_ACTIVE")

    def test_trigger_and_run_commands_are_owner_scoped(self) -> None:
        trigger = self.create_trigger()
        fired = self.automation.fire_trigger(
            "user-1", trigger["trigger_id"], "owner-scope"
        )
        with self.assertRaises(TaskAutomationError) as trigger_error:
            self.automation.get_trigger("user-2", trigger["trigger_id"])
        self.assertEqual(trigger_error.exception.code, "TRIGGER_NOT_FOUND")
        with self.assertRaises(TaskAutomationError) as run_error:
            self.automation.list_commands(
                "user-2", fired["run"]["run_id"]
            )
        self.assertEqual(run_error.exception.code, "RUN_NOT_FOUND")

    def test_commands_are_idempotent_and_acknowledged_once(self) -> None:
        fired = self.automation.fire_trigger(
            "user-1", self.create_trigger()["trigger_id"], "steering"
        )
        run_id = fired["run"]["run_id"]
        values = {
            "command_type": "follow_up",
            "instruction": "Include the deployment evidence.",
            "payload": {"priority": "high"},
            "idempotency_key": "follow-up-1",
        }
        first = self.automation.submit_command("user-1", run_id, values)
        duplicate = self.automation.submit_command("user-1", run_id, values)
        self.assertEqual(first["command_id"], duplicate["command_id"])
        self.assertEqual(
            [item["command_id"] for item in self.automation.list_commands(
                "user-1", run_id, "pending"
            )],
            [first["command_id"]],
        )

        acknowledged = self.automation.acknowledge_command(
            "user-1", run_id, first["command_id"]
        )
        replay = self.automation.acknowledge_command(
            "user-1", run_id, first["command_id"]
        )
        self.assertEqual(acknowledged["status"], "acknowledged")
        self.assertEqual(acknowledged["command_id"], replay["command_id"])
        events = self.execution.list_events("user-1", run_id)
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types.count("run.command_added"), 1)
        self.assertEqual(event_types.count("run.command_acknowledged"), 1)

    def test_terminal_run_rejects_new_command(self) -> None:
        goal = self.create_goal()
        run = self.execution.create_run(
            "user-1", goal["goal_id"], {"steps": [{"title": "Finish"}]}
        )
        run = self.execution.start_run("user-1", run["run_id"])
        step_id = run["steps"][0]["step_id"]
        self.execution.start_step("user-1", run["run_id"], step_id)
        self.execution.complete_step("user-1", run["run_id"], step_id)
        with self.assertRaises(TaskAutomationError) as context:
            self.automation.submit_command(
                "user-1",
                run["run_id"],
                {"command_type": "instruction", "instruction": "Do more"},
            )
        self.assertEqual(context.exception.code, "RUN_COMMANDS_CLOSED")

    def test_firing_record_and_event_are_atomic(self) -> None:
        trigger = self.create_trigger()
        connection = self.database.get_connection()
        connection.execute(
            """CREATE TRIGGER fail_trigger_fired_event
               BEFORE INSERT ON task_events
               WHEN NEW.event_type = 'trigger.fired'
               BEGIN
                   SELECT RAISE(ABORT, 'event append failed');
               END"""
        )
        connection.commit()
        connection.close()

        with self.assertRaises(sqlite3.IntegrityError):
            self.automation.fire_trigger(
                "user-1", trigger["trigger_id"], "atomic-source"
            )
        connection = self.database.get_connection()
        firing_count = connection.execute(
            "SELECT COUNT(*) FROM task_trigger_firings WHERE trigger_id = ?",
            (trigger["trigger_id"],),
        ).fetchone()[0]
        last_fired_at = connection.execute(
            "SELECT last_fired_at FROM task_triggers WHERE trigger_id = ?",
            (trigger["trigger_id"],),
        ).fetchone()[0]
        run_count = connection.execute(
            "SELECT COUNT(*) FROM task_runs WHERE user_id = ?", ("user-1",)
        ).fetchone()[0]
        connection.execute("DROP TRIGGER fail_trigger_fired_event")
        connection.commit()
        connection.close()
        self.assertEqual(firing_count, 0)
        self.assertIsNone(last_fired_at)
        self.assertEqual(run_count, 1)

        recovered = self.automation.fire_trigger(
            "user-1", trigger["trigger_id"], "atomic-source"
        )
        self.assertEqual(recovered["run"]["run_id"], recovered["firing"]["run_id"])
        connection = self.database.get_connection()
        self.assertEqual(
            connection.execute(
                "SELECT COUNT(*) FROM task_runs WHERE user_id = ?", ("user-1",)
            ).fetchone()[0],
            1,
        )
        connection.close()

    def test_command_and_event_are_atomic(self) -> None:
        fired = self.automation.fire_trigger(
            "user-1", self.create_trigger()["trigger_id"], "command-atomic"
        )
        run_id = fired["run"]["run_id"]
        connection = self.database.get_connection()
        connection.execute(
            """CREATE TRIGGER fail_command_event
               BEFORE INSERT ON task_events
               WHEN NEW.event_type = 'run.command_added'
               BEGIN
                   SELECT RAISE(ABORT, 'event append failed');
               END"""
        )
        connection.commit()
        connection.close()
        with self.assertRaises(sqlite3.IntegrityError):
            self.automation.submit_command(
                "user-1",
                run_id,
                {"command_type": "instruction", "instruction": "Inspect tests"},
            )
        self.assertEqual(self.automation.list_commands("user-1", run_id), [])


if __name__ == "__main__":
    unittest.main()
