"""Behavior tests for user-managed task categories."""
from pathlib import Path
import tempfile
import unittest

from database import Database


class TaskCategoryTests(unittest.TestCase):
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

    def test_update_is_scoped_to_its_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "categories.db")
            self._create_user(database, "owner")
            self._create_user(database, "other-user")
            category_id = database.add_task_category("owner", "Personal")

            updated = database.update_task_category(
                category_id,
                "other-user",
                category_name="Renamed",
            )

            self.assertFalse(updated)
            self.assertEqual(
                database.get_user_task_categories("owner")[0]["category_name"],
                "Personal",
            )

    def test_preset_categories_are_protected_from_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "categories.db")
            self._create_user(database, "owner")
            category_id = database.add_task_category(
                "owner",
                "Preset",
                is_preset=1,
            )

            deleted = database.delete_task_category(category_id, "owner")

            self.assertFalse(deleted)
            self.assertEqual(len(database.get_user_task_categories("owner")), 1)


if __name__ == "__main__":
    unittest.main()
