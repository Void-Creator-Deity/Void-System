"""Reward marketplace business rules and stable public results."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.reward_marketplace_contracts import RewardMarketplaceError, RewardMarketplaceRepository
from modules.reward_marketplace.catalog import ITEMS_BY_ID, MARKETPLACE_ITEMS


class RewardMarketplace:
    def __init__(self, repository: RewardMarketplaceRepository) -> None:
        self._repository = repository

    def list_items(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        return [
            dict(item)
            for item in MARKETPLACE_ITEMS
            if category is None or item["category"] == category
        ]

    def purchase(self, user_id: str, item_id: str, quantity: int) -> Dict[str, Any]:
        item = ITEMS_BY_ID.get(item_id)
        if item is None:
            raise RewardMarketplaceError("商品不存在", "ITEM_NOT_FOUND", 404)

        remaining_balance = self._repository.purchase(
            user_id=user_id,
            item_id=item_id,
            item_name=str(item["item_name"]),
            quantity=quantity,
            unit_price=int(item["price"]),
        )
        if remaining_balance is None:
            raise RewardMarketplaceError("余额不足", "INSUFFICIENT_BALANCE")

        return {
            "item_id": item_id,
            "item_name": item["item_name"],
            "quantity": quantity,
            "total_price": int(item["price"]) * quantity,
            "remaining_balance": remaining_balance,
        }
