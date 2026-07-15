"""Behavior tests for atomic Reward Marketplace settlement."""
from pathlib import Path
import tempfile
import unittest

from database import Database


class RewardMarketplaceTests(unittest.TestCase):
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

    def test_purchase_updates_ledger_inventory_and_history_together(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "market.db")
            self._create_user(database, "buyer")
            database.add_coins("buyer", 100, source="test")

            remaining = database.purchase_reward_item(
                "buyer",
                "item_energy_small",
                "Small energy",
                quantity=2,
                unit_price=30,
            )

            self.assertEqual(remaining, 40)
            self.assertEqual(database.get_user_balance("buyer"), 40)
            self.assertEqual(
                database.get_user_resources("buyer")["shop_item_energy_small"],
                2,
            )
            connection = database.get_connection()
            try:
                history = connection.execute(
                    "SELECT quantity, total_price FROM purchase_history WHERE user_id = ?",
                    ("buyer",),
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(tuple(history), (2, 60))

    def test_insufficient_balance_does_not_create_partial_purchase(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "market.db")
            self._create_user(database, "buyer")
            database.add_coins("buyer", 20, source="test")

            remaining = database.purchase_reward_item(
                "buyer",
                "item_energy_small",
                "Small energy",
                quantity=1,
                unit_price=50,
            )

            self.assertIsNone(remaining)
            self.assertEqual(database.get_user_balance("buyer"), 20)
            self.assertEqual(database.get_user_resources("buyer"), {})
            connection = database.get_connection()
            try:
                purchases = connection.execute(
                    "SELECT COUNT(*) FROM purchase_history WHERE user_id = ?",
                    ("buyer",),
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(purchases, 0)


if __name__ == "__main__":
    unittest.main()
