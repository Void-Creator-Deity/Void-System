"""Composition for the analytics dashboard."""
from adapters.sqlite.analytics_repository import SQLiteAnalyticsRepository
from database import Database
from modules.analytics.dashboard import AnalyticsDashboard


def get_analytics_dashboard(database: Database) -> AnalyticsDashboard:
    return AnalyticsDashboard(SQLiteAnalyticsRepository(database.get_connection))
