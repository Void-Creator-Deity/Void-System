"""User-facing analytics read-model orchestration."""
from __future__ import annotations

from typing import Any, Dict

from core.analytics_contracts import AnalyticsRepository


class AnalyticsDashboard:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self._repository = repository

    def overview(self, user_id: str) -> Dict[str, Any]:
        return self._repository.user_overview(user_id)
