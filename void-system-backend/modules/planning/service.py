"""Composition point for planning and evaluation engines."""
from __future__ import annotations

from typing import Optional

from adapters.legacy.planning_adapters import LegacyAdvisorPlanningEngine, LegacyTaskEvaluationEngine
from core.planning_contracts import EvaluationEngine, PlanningEngine
from core.runtime_settings import RuntimeSettings


def get_planning_engine(settings: Optional[RuntimeSettings] = None) -> PlanningEngine:
    """Create a planning adapter bound to one application runtime."""
    return LegacyAdvisorPlanningEngine(settings=settings)


def get_evaluation_engine(settings: Optional[RuntimeSettings] = None) -> EvaluationEngine:
    """Create an evaluation adapter bound to one application runtime."""
    return LegacyTaskEvaluationEngine(settings=settings)
