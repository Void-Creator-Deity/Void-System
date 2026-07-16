"""Compatibility projection tests for the legacy task APIs."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from adapters.sqlite.migrations import Migration, run_migrations
from database import Database


class TaskExecutionProjectionTests(unittest.TestCase):
    @staticmethod
    def _create_user(database: Database, user_id: str) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, user_id)
            )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _step(title: str) -> dict:
        return {
            "title": title,
            "description": f"{title} description",
            "related_attrs": {},
            "estimated_time": 30,
            "reward_coins": 10,
            "priority": "medium",
            "attribute_points": 0,
            "completion_type": "simple",
            "completion_criteria": {"done": True},
            "task_type": "main",
            "is_optional": False,
            "is_daily": False,
        }

    def test_standalone_task_lifecycle_projects_into_one_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "projection.db")
            self._create_user(database, "owner")

            task_id = database.add_task("owner", "Prepare release")
            connection = database.get_connection()
            try:
                link = connection.execute(
                    "SELECT * FROM legacy_task_execution_links WHERE legacy_task_id = ?",
                    (task_id,),
                ).fetchone()
                step = connection.execute(
                    "SELECT status, progress FROM task_steps WHERE step_id = ?", (link["step_id"],)
                ).fetchone()
                run = connection.execute(
                    "SELECT status FROM task_runs WHERE run_id = ?", (link["run_id"],)
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(step["status"], "ready")
            self.assertEqual(run["status"], "queued")

            self.assertTrue(database.update_task_status(task_id, "owner", "in_progress"))
            self.assertTrue(database.update_task_progress(task_id, "owner", 45))
            self.assertTrue(database.submit_task_proof(task_id, "owner", {"note": "done"}))
            connection = database.get_connection()
            try:
                step = connection.execute(
                    "SELECT status, progress FROM task_steps WHERE step_id = ?", (link["step_id"],)
                ).fetchone()
                run = connection.execute(
                    "SELECT status FROM task_runs WHERE run_id = ?", (link["run_id"],)
                ).fetchone()
                approvals = connection.execute(
                    "SELECT status FROM task_approvals WHERE step_id = ?", (link["step_id"],)
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual((step["status"], step["progress"]), ("waiting_approval", 45))
            self.assertEqual(run["status"], "waiting_approval")
            self.assertEqual([row["status"] for row in approvals], ["pending"])

            self.assertTrue(database.update_task_status(task_id, "owner", "completed"))
            connection = database.get_connection()
            try:
                step = connection.execute(
                    "SELECT status, progress FROM task_steps WHERE step_id = ?", (link["step_id"],)
                ).fetchone()
                run = connection.execute(
                    "SELECT status FROM task_runs WHERE run_id = ?", (link["run_id"],)
                ).fetchone()
                goal = connection.execute(
                    "SELECT status FROM task_goals WHERE goal_id = ?", (link["goal_id"],)
                ).fetchone()
                approval = connection.execute(
                    "SELECT status FROM task_approvals WHERE step_id = ?", (link["step_id"],)
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual((step["status"], step["progress"]), ("completed", 100))
            self.assertEqual(run["status"], "completed")
            self.assertEqual(goal["status"], "completed")
            self.assertEqual(approval["status"], "approved")

    def test_chain_projects_to_one_dependency_graph_and_unlocks_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "chain.db")
            self._create_user(database, "owner")
            chain_id = database.create_task_chain("owner", "Release workflow")
            task_ids = database.create_task_chain_steps(
                "owner", chain_id, [self._step("Plan"), self._step("Build"), self._step("Review")]
            )

            connection = database.get_connection()
            try:
                chain_link = connection.execute(
                    "SELECT * FROM legacy_chain_execution_links WHERE legacy_chain_id = ?",
                    (chain_id,),
                ).fetchone()
                links = connection.execute(
                    """SELECT l.legacy_task_id, l.goal_id, l.run_id, l.step_id, s.status, s.position
                       FROM legacy_task_execution_links l
                       JOIN task_steps s ON s.step_id = l.step_id
                       WHERE l.legacy_chain_id = ? ORDER BY s.position""",
                    (chain_id,),
                ).fetchall()
                dependencies = connection.execute(
                    "SELECT step_id, depends_on_step_id FROM task_step_dependencies WHERE run_id = ?",
                    (chain_link["run_id"],),
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual([row["legacy_task_id"] for row in links], task_ids)
            self.assertEqual({row["goal_id"] for row in links}, {chain_link["goal_id"]})
            self.assertEqual({row["run_id"] for row in links}, {chain_link["run_id"]})
            self.assertEqual([row["status"] for row in links], ["ready", "pending", "pending"])
            self.assertEqual(len(dependencies), 2)

            self.assertTrue(database.update_task_status(task_ids[0], "owner", "completed"))
            connection = database.get_connection()
            try:
                statuses = connection.execute(
                    "SELECT status FROM task_steps WHERE run_id = ? ORDER BY position",
                    (chain_link["run_id"],),
                ).fetchall()
                run = connection.execute(
                    "SELECT status FROM task_runs WHERE run_id = ?", (chain_link["run_id"],)
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual([row["status"] for row in statuses], ["completed", "ready", "pending"])
            self.assertEqual(run["status"], "running")

    def test_projection_is_owner_scoped_and_deleted_with_legacy_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "owners.db")
            self._create_user(database, "owner")
            self._create_user(database, "other")
            task_id = database.add_task("owner", "Private task")
            self.assertFalse(database.update_task_status(task_id, "other", "completed"))
            self.assertFalse(database.delete_task(task_id, "other"))

            connection = database.get_connection()
            try:
                link = connection.execute(
                    "SELECT goal_id FROM legacy_task_execution_links WHERE legacy_task_id = ?",
                    (task_id,),
                ).fetchone()
            finally:
                connection.close()
            self.assertIsNotNone(link)
            self.assertTrue(database.delete_task(task_id, "owner"))
            connection = database.get_connection()
            try:
                task_count = connection.execute(
                    "SELECT COUNT(*) FROM tasks WHERE task_id = ?", (task_id,)
                ).fetchone()[0]
                goal_count = connection.execute(
                    "SELECT COUNT(*) FROM task_goals WHERE goal_id = ?", (link["goal_id"],)
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual((task_count, goal_count), (0, 0))

    def test_migration_backfills_existing_legacy_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backfill.db"
            database = Database(path)
            self._create_user(database, "owner")
            task_id = database.add_task("owner", "Existing task")
            connection = database.get_connection()
            try:
                connection.execute("DELETE FROM legacy_task_execution_links")
                connection.execute("DELETE FROM task_goals")
                connection.execute("DELETE FROM schema_migrations WHERE version = 10")
                connection.commit()
            finally:
                connection.close()

            Database(path)
            connection = database.get_connection()
            try:
                link = connection.execute(
                    "SELECT run_id, step_id FROM legacy_task_execution_links WHERE legacy_task_id = ?",
                    (task_id,),
                ).fetchone()
                step = connection.execute(
                    "SELECT status FROM task_steps WHERE step_id = ?", (link["step_id"],)
                ).fetchone()
            finally:
                connection.close()
            self.assertIsNotNone(link)
            self.assertEqual(step["status"], "ready")


    def test_new_legacy_writes_start_from_canonical_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "canonical-first.db")
            self._create_user(database, "owner")
            task_id = database.add_task("owner", "Canonical-first task")
            chain_id = database.create_task_chain("owner", "Canonical-first workflow")
            database.create_task_chain_steps(
                "owner", chain_id, [self._step("Prepare"), self._step("Confirm")]
            )

            connection = database.get_connection()
            try:
                task_run = connection.execute(
                    """SELECT run_id FROM legacy_task_execution_links
                       WHERE legacy_task_id = ?""",
                    (task_id,),
                ).fetchone()
                chain_run = connection.execute(
                    """SELECT run_id FROM legacy_chain_execution_links
                       WHERE legacy_chain_id = ?""",
                    (chain_id,),
                ).fetchone()
                task_events = {
                    row["event_type"]
                    for row in connection.execute(
                        "SELECT event_type FROM task_events WHERE run_id = ?",
                        (task_run["run_id"],),
                    ).fetchall()
                }
                chain_events = {
                    row["event_type"]
                    for row in connection.execute(
                        "SELECT event_type FROM task_events WHERE run_id = ?",
                        (chain_run["run_id"],),
                    ).fetchall()
                }
            finally:
                connection.close()

            self.assertIn("legacy.task_canonical_created", task_events)
            self.assertNotIn("legacy.task_projected", task_events)
            self.assertIn("legacy.chain_canonical_created", chain_events)
            self.assertNotIn("legacy.chain_projected", chain_events)

    def test_compatibility_updates_follow_canonical_step_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "canonical-first-updates.db")
            self._create_user(database, "owner")
            task_id = database.add_task("owner", "Verify compatibility ordering")
            connection = database.get_connection()
            try:
                link = connection.execute(
                    "SELECT step_id FROM legacy_task_execution_links WHERE legacy_task_id = ?",
                    (task_id,),
                ).fetchone()
                step_id = str(link["step_id"])
                connection.executescript(
                    f"""
                    CREATE TRIGGER canonical_status_before_legacy
                    BEFORE UPDATE OF status ON tasks
                    WHEN NEW.task_id = '{task_id}'
                         AND NEW.status = 'in_progress'
                         AND COALESCE((SELECT status FROM task_steps
                                       WHERE step_id = '{step_id}'), '') != 'running'
                    BEGIN
                        SELECT RAISE(ABORT, 'canonical status must be written first');
                    END;
                    CREATE TRIGGER canonical_progress_before_legacy
                    BEFORE UPDATE OF current_progress ON tasks
                    WHEN NEW.task_id = '{task_id}'
                         AND COALESCE((SELECT progress FROM task_steps
                                       WHERE step_id = '{step_id}'), -1) != NEW.current_progress
                    BEGIN
                        SELECT RAISE(ABORT, 'canonical progress must be written first');
                    END;
                    CREATE TRIGGER canonical_proof_before_legacy
                    BEFORE UPDATE OF proof_data ON tasks
                    WHEN NEW.task_id = '{task_id}'
                         AND COALESCE((SELECT status FROM task_steps
                                       WHERE step_id = '{step_id}'), '') != 'waiting_approval'
                    BEGIN
                        SELECT RAISE(ABORT, 'canonical proof state must be written first');
                    END;
                    """
                )
                connection.commit()
            finally:
                connection.close()

            self.assertTrue(database.update_task_status(task_id, "owner", "in_progress"))
            self.assertTrue(database.update_task_progress(task_id, "owner", 55))
            self.assertTrue(database.submit_task_proof(task_id, "owner", {"note": "verified"}))
            connection = database.get_connection()
            try:
                events = {
                    row["event_type"]
                    for row in connection.execute(
                        "SELECT event_type FROM task_events WHERE step_id = ?", (step_id,)
                    ).fetchall()
                }
            finally:
                connection.close()
            self.assertIn("legacy.task.progress_updated", events)

    def test_chain_append_creates_canonical_steps_before_compatibility_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "canonical-chain-append.db")
            self._create_user(database, "owner")
            chain_id = database.create_task_chain("owner", "Release workflow")
            first_ids = database.create_task_chain_steps(
                "owner", chain_id, [self._step("Prepare"), self._step("Review")]
            )
            appended_ids = database.create_task_chain_steps(
                "owner", chain_id, [self._step("Publish")]
            )
            self.assertEqual(len(appended_ids), 1)

            connection = database.get_connection()
            try:
                rows = connection.execute(
                    """SELECT task_id, chain_order FROM tasks
                       WHERE chain_id = ? AND user_id = ? ORDER BY chain_order""",
                    (chain_id, "owner"),
                ).fetchall()
                appended_link = connection.execute(
                    "SELECT run_id, step_id FROM legacy_task_execution_links WHERE legacy_task_id = ?",
                    (appended_ids[0],),
                ).fetchone()
                previous_link = connection.execute(
                    "SELECT step_id FROM legacy_task_execution_links WHERE legacy_task_id = ?",
                    (first_ids[-1],),
                ).fetchone()
                dependency = connection.execute(
                    """SELECT 1 FROM task_step_dependencies
                       WHERE run_id = ? AND step_id = ? AND depends_on_step_id = ?""",
                    (appended_link["run_id"], appended_link["step_id"], previous_link["step_id"]),
                ).fetchone()
                events = {
                    row["event_type"]
                    for row in connection.execute(
                        "SELECT event_type FROM task_events WHERE run_id = ?",
                        (appended_link["run_id"],),
                    ).fetchall()
                }
            finally:
                connection.close()

            self.assertEqual([int(row["chain_order"]) for row in rows], [1, 2, 3])
            self.assertIsNotNone(dependency)
            self.assertIn("legacy.chain_canonical_extended", events)
            self.assertNotIn("legacy.chain_extended", events)
    def test_moving_a_task_to_a_chain_creates_target_step_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "canonical-task-move.db")
            self._create_user(database, "owner")
            task_id = database.add_task("owner", "Standalone task")
            chain_id = database.create_task_chain("owner", "Release workflow")
            chain_task_ids = database.create_task_chain_steps(
                "owner", chain_id, [self._step("Prepare"), self._step("Review")]
            )
            connection = database.get_connection()
            try:
                connection.executescript(
                    f"""
                    CREATE TRIGGER canonical_move_before_compatibility_update
                    BEFORE UPDATE OF chain_id ON tasks
                    WHEN NEW.task_id = '{task_id}' AND NEW.chain_id = '{chain_id}'
                         AND NOT EXISTS (
                             SELECT 1 FROM task_events
                             WHERE event_type = 'legacy.chain_canonical_extended'
                         )
                    BEGIN
                        SELECT RAISE(ABORT, 'target canonical step must be written first');
                    END;
                    """
                )
                connection.commit()
            finally:
                connection.close()

            self.assertTrue(database.add_task_to_chain(task_id, chain_id, 3))
            connection = database.get_connection()
            try:
                task = connection.execute(
                    "SELECT chain_id, chain_order, prerequisites FROM tasks WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
                link = connection.execute(
                    """SELECT legacy_chain_id, run_id, step_id
                       FROM legacy_task_execution_links WHERE legacy_task_id = ?""",
                    (task_id,),
                ).fetchone()
                previous_link = connection.execute(
                    "SELECT step_id FROM legacy_task_execution_links WHERE legacy_task_id = ?",
                    (chain_task_ids[-1],),
                ).fetchone()
                dependency = connection.execute(
                    """SELECT 1 FROM task_step_dependencies
                       WHERE run_id = ? AND step_id = ? AND depends_on_step_id = ?""",
                    (link["run_id"], link["step_id"], previous_link["step_id"]),
                ).fetchone()
                events = {
                    row["event_type"]
                    for row in connection.execute(
                        "SELECT event_type FROM task_events WHERE run_id = ?",
                        (link["run_id"],),
                    ).fetchall()
                }
            finally:
                connection.close()

            self.assertEqual((task["chain_id"], int(task["chain_order"])), (chain_id, 3))
            self.assertEqual(json.loads(task["prerequisites"]), [chain_task_ids[-1]])
            self.assertEqual(link["legacy_chain_id"], chain_id)
            self.assertIsNotNone(dependency)
            self.assertIn("legacy.chain_canonical_extended", events)

if __name__ == "__main__":
    unittest.main()
