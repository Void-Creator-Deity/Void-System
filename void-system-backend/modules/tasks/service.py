"""Composition point for canonical Goal, Run, Step, and Trigger services."""
from __future__ import annotations

from adapters.sqlite.task_automation_repository import SQLiteTaskAutomationRepository
from adapters.sqlite.task_execution_repository import SQLiteTaskExecutionRepository
from core.runtime_settings import RuntimeSettings
from database import Database
from modules.tasks.automation import TaskAutomation
from modules.tasks.execution import TaskExecution


def get_task_execution(
    database: Database,
    settings: RuntimeSettings | None = None,
) -> TaskExecution:
    """Compose durable execution with conservative review-memory adapters."""
    from adapters.sqlite.personal_context_repository import SQLitePersonalContextRepository
    from modules.personal_context.observation_adapters import (
        TaskReviewMemoryCandidateAdapter,
        TaskReviewObservationAdapter,
    )
    from modules.personal_context.profile import ProfileCognition
    from modules.planning.service import get_evaluation_engine

    context_repository = SQLitePersonalContextRepository(database.get_connection)
    profile = ProfileCognition(context_repository)
    return TaskExecution(
        SQLiteTaskExecutionRepository(database.get_connection),
        run_review_observation_sink=TaskReviewObservationAdapter(profile),
        run_review_memory_candidate_sink=TaskReviewMemoryCandidateAdapter(context_repository),
        evaluation_engine=get_evaluation_engine(settings),
    )


def get_task_automation(
    database: Database,
    settings: RuntimeSettings | None = None,
) -> TaskAutomation:
    """Compose Trigger-to-Run automation over canonical Task Execution."""
    repository = SQLiteTaskAutomationRepository(database.get_connection)
    return TaskAutomation(repository, get_task_execution(database, settings))
