"""SQLite persistence for atomic Reward Marketplace settlement."""
from __future__ import annotations

import uuid
from typing import Optional

from adapters.sqlite.task_repository import ConnectionFactory
from core.reward_marketplace_contracts import RewardMarketplaceRepository


class SQLiteRewardMarketplaceRepository(RewardMarketplaceRepository):
    """Persists a purchase as one immediate SQLite transaction."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def purchase(
        self,
        user_id: str,
        item_id: str,
        item_name: str,
        quantity: int,
        unit_price: int,
    ) -> Optional[int]:
        total_price = quantity * unit_price
        resource_key = f"shop_{item_id}"
        conn = self._connection_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            balance_row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM coins WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            balance = int(balance_row[0] or 0)
            if balance < total_price:
                conn.rollback()
                return None

            conn.execute(
                """INSERT INTO coins (record_id, user_id, amount, type, source)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    user_id,
                    -total_price,
                    "spend",
                    f"reward_marketplace:{item_id}",
                ),
            )
            resource = conn.execute(
                "SELECT resource_id FROM user_resources WHERE user_id = ? AND resource_key = ?",
                (user_id, resource_key),
            ).fetchone()
            if resource is not None:
                conn.execute(
                    "UPDATE user_resources SET quantity = quantity + ? WHERE resource_id = ?",
                    (quantity, resource[0]),
                )
            else:
                conn.execute(
                    """INSERT INTO user_resources
                       (resource_id, user_id, resource_key, quantity)
                       VALUES (?, ?, ?, ?)""",
                    (str(uuid.uuid4()), user_id, resource_key, quantity),
                )
            conn.execute(
                """INSERT INTO purchase_history
                   (purchase_id, user_id, item_id, item_name, quantity, unit_price, total_price)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    user_id,
                    item_id,
                    item_name,
                    quantity,
                    unit_price,
                    total_price,
                ),
            )
            conn.commit()
            return balance - total_price
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
