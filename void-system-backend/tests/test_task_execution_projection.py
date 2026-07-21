"""One-time retirement tests for the legacy task schema."""
from pathlib import Path
import json
import tempfile
import unittest

from database import Database


class LegacyTaskRetirementTests(unittest.TestCase):
    def test_legacy_task_is_materialized_before_legacy_tables_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "retirement.db")
            connection = database.get_connection()
            try:
                connection.execute("INSERT INTO users (user_id, username) VALUES ('owner', 'owner')")
                connection.execute(
                    """CREATE TABLE tasks (
                        task_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, task_name TEXT NOT NULL,
                        description TEXT, status TEXT, priority TEXT, current_progress INTEGER,
                        completion_criteria TEXT, chain_id TEXT, chain_order INTEGER,
                        prerequisites TEXT, created_at TEXT
                    )"""
                )
                connection.execute(
                    """CREATE TABLE task_chains (
                        chain_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, chain_name TEXT,
                        description TEXT, created_at TEXT
                    )"""
                )
                connection.execute(
                    """INSERT INTO tasks
                       (task_id, user_id, task_name, description, status, priority,
                        current_progress, completion_criteria, chain_order, prerequisites, created_at)
                       VALUES ('legacy-step', 'owner', 'Ship migration', 'Move safely', 'completed',
                               'high', 100, '{"done": true}', 0, '[]', '2026-07-18T00:00:00')"""
                )
                database._add_legacy_task_execution_projection(connection)
                database._retire_legacy_task_tables(connection)
                connection.commit()

                step = connection.execute(
                    """SELECT title, status, progress, completion_criteria
                       FROM task_steps WHERE user_id = 'owner'"""
                ).fetchone()
                run_count = connection.execute(
                    "SELECT COUNT(*) FROM task_runs WHERE user_id = 'owner'"
                ).fetchone()[0]
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
            finally:
                connection.close()

        self.assertEqual((step["title"], step["status"], step["progress"]), ("Ship migration", "completed", 100))
        self.assertEqual(json.loads(step["completion_criteria"]), {"done": True})
        self.assertEqual(run_count, 1)
        self.assertFalse({"tasks", "task_chains", "task_categories", "legacy_task_execution_links", "legacy_chain_execution_links"} & tables)


if __name__ == "__main__":
    unittest.main()
