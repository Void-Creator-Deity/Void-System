"""Composition point for the Task Workflow module."""
from __future__ import annotations

from adapters.sqlite.task_automation_repository import SQLiteTaskAutomationRepository
from adapters.sqlite.task_execution_repository import SQLiteTaskExecutionRepository
from adapters.sqlite.task_repository import SQLiteTaskRepository
from adapters.sqlite.task_workspace_repository import SQLiteTaskWorkspaceRepository
from core.planning_contracts import EvaluationEngine, PlanningEngine
from core.runtime_settings import RuntimeSettings
from database import Database
from modules.tasks.automation import TaskAutomation
from modules.planning.service import get_planning_engine
from modules.tasks.execution import TaskExecution
from modules.tasks.workspace import TaskWorkspace
from modules.tasks.workflow import TaskWorkflow


def get_task_workflow(database: Database, evaluator: EvaluationEngine | None = None) -> TaskWorkflow:
    repository = SQLiteTaskRepository(database.get_connection)
    return TaskWorkflow(repository, evaluator=evaluator)


def get_task_workspace(
    database: Database,
    evaluator: EvaluationEngine | None = None,
    planner: PlanningEngine | None = None,
    settings: RuntimeSettings | None = None,
) -> TaskWorkspace:
    """Compose the task workspace over focused adapters owned by the application."""
    repository = SQLiteTaskWorkspaceRepository(database.get_connection)
    workflow = get_task_workflow(database, evaluator=evaluator)
    return TaskWorkspace(
        repository, workflow, planner=planner or get_planning_engine(settings)
    )


def get_task_execution(database: Database) -> TaskExecution:
    """Compose the durable Goal and Run execution Module."""
    return TaskExecution(SQLiteTaskExecutionRepository(database.get_connection))


def get_task_automation(database: Database) -> TaskAutomation:
    """Compose Trigger-to-Run automation over canonical Task Execution."""
    repository = SQLiteTaskAutomationRepository(database.get_connection)
    return TaskAutomation(repository, get_task_execution(database))
