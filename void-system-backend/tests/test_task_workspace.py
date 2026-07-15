"""Behavior tests for user-scoped Task Workspace persistence."""
from pathlib import Path
import json
import tempfile
import unittest

from database import Database


class TaskWorkspaceTests(unittest.TestCase):
    @staticmethod
    def _create_user(database: Database, user_id: str) -> None:
        connection = database.get_connection()
        try:
            connection.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                (user_id, user_id),
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
            "completion_criteria": {},
            "task_type": "main",
            "is_optional": False,
            "is_daily": False,
        }

    def test_task_delete_is_scoped_to_its_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "tasks.db")
            self._create_user(database, "owner")
            self._create_user(database, "other-user")
            task_id = database.add_task("owner", "Protected task")

            self.assertFalse(database.delete_task(task_id, "other-user"))
            connection = database.get_connection()
            try:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM tasks WHERE task_id = ? AND user_id = ?",
                        (task_id, "owner"),
                    ).fetchone()[0],
                    1,
                )
            finally:
                connection.close()
            self.assertTrue(database.delete_task(task_id, "owner"))
            connection = database.get_connection()
            try:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM tasks WHERE task_id = ?",
                        (task_id,),
                    ).fetchone()[0],
                    0,
                )
            finally:
                connection.close()

    def test_task_chain_delete_is_scoped_to_its_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "tasks.db")
            self._create_user(database, "owner")
            self._create_user(database, "other-user")
            chain_id = database.create_task_chain("owner", "Protected workflow")

            self.assertFalse(database.delete_task_chain(chain_id, "other-user"))
            self.assertIsNotNone(database.get_task_chain(chain_id, "owner"))

    def test_workflow_steps_are_ordered_and_linked_by_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "tasks.db")
            self._create_user(database, "owner")
            chain_id = database.create_task_chain("owner", "Launch workflow", generation_status="queued")

            task_ids = database.create_task_chain_steps(
                "owner",
                chain_id,
                [self._step("Discover"), self._step("Build"), self._step("Review")],
            )

            connection = database.get_connection()
            try:
                rows = connection.execute(
                    "SELECT task_id, prerequisites FROM tasks WHERE chain_id = ? ORDER BY chain_order",
                    (chain_id,),
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual(task_ids, [row[0] for row in rows])
            self.assertEqual(json.loads(rows[0][1]), [])
            self.assertEqual(json.loads(rows[1][1]), [task_ids[0]])
            self.assertEqual(json.loads(rows[2][1]), [task_ids[1]])
            chain = database.get_task_chain(chain_id, "owner")
            self.assertEqual(chain["generation_status"], "ready")
            self.assertIsNone(chain["generation_error"])

    def test_workflow_step_creation_rolls_back_on_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "tasks.db")
            self._create_user(database, "owner")
            chain_id = database.create_task_chain("owner", "Atomic workflow")
            invalid_step = self._step("Broken")
            del invalid_step["title"]

            with self.assertRaises(KeyError):
                database.create_task_chain_steps(
                    "owner", chain_id, [self._step("First"), invalid_step]
                )

            connection = database.get_connection()
            try:
                count = connection.execute(
                    "SELECT COUNT(*) FROM tasks WHERE chain_id = ?",
                    (chain_id,),
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(count, 0)

    def test_generation_state_cannot_be_changed_by_another_user(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "tasks.db")
            self._create_user(database, "owner")
            self._create_user(database, "other-user")
            chain_id = database.create_task_chain("owner", "Protected workflow", generation_status="queued")

            self.assertFalse(
                database.update_task_chain_generation_state(
                    chain_id, "other-user", "failed", "not allowed"
                )
            )
            chain = database.get_task_chain(chain_id, "owner")
            self.assertEqual(chain["generation_status"], "queued")
            self.assertIsNone(chain["generation_error"])


if __name__ == "__main__":
    unittest.main()
