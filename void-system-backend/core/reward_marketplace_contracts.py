"""Contracts for atomic Reward Marketplace purchases."""
from __future__ import annotations

from typing import Optional, Protocol


class RewardMarketplaceError(Exception):
    """Expected marketplace failures for HTTP adapters to translate."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class RewardMarketplaceRepository(Protocol):
    def purchase(
        self,
        user_id: str,
        item_id: str,
        item_name: str,
        quantity: int,
        unit_price: int,
    ) -> Optional[int]:
        """Return remaining balance or None when funds are insufficient."""
