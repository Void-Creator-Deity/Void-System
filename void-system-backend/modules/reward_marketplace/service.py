"""Composition for the Reward Marketplace module."""
from adapters.sqlite.reward_marketplace_repository import SQLiteRewardMarketplaceRepository
from database import Database
from modules.reward_marketplace.marketplace import RewardMarketplace


def get_reward_marketplace(database: Database) -> RewardMarketplace:
    return RewardMarketplace(SQLiteRewardMarketplaceRepository(database.get_connection))
