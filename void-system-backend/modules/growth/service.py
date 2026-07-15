"""Composition for the Growth Profile module."""
from adapters.sqlite.growth_repository import SQLiteGrowthProfileRepository
from database import Database
from modules.growth.profile import GrowthProfile


def get_growth_profile(database: Database) -> GrowthProfile:
    return GrowthProfile(SQLiteGrowthProfileRepository(database.get_connection))
