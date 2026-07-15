"""Behavior tests for user-managed growth attributes."""
from pathlib import Path
import tempfile
import unittest

from database import Database


class GrowthProfileTests(unittest.TestCase):
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

    def test_attribute_name_is_persisted_when_updated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "growth.db")
            user_id = "growth-user"
            self._create_user(database, user_id)
            attr_id = database.add_attribute(user_id, "Focus", max_value=100)

            updated = database.update_attribute(attr_id, attr_name="Deep focus")
            attributes = database.get_user_attributes(user_id)

            self.assertTrue(updated)
            self.assertEqual(attributes[0]["attr_name"], "Deep focus")

    def test_lowering_maximum_can_clamp_existing_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "growth.db")
            user_id = "growth-user"
            self._create_user(database, user_id)
            attr_id = database.add_attribute(user_id, "Energy", max_value=100)
            database.update_attribute_value(attr_id, 80)

            updated = database.update_attribute(attr_id, attr_value=40, max_value=40)
            attributes = database.get_user_attributes(user_id)

            self.assertTrue(updated)
            self.assertEqual(attributes[0]["max_value"], 40)
            self.assertEqual(attributes[0]["attr_value"], 40)


if __name__ == "__main__":
    unittest.main()
