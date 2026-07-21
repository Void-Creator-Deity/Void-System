"""Canonical Goal, Run, Step, and Trigger lifecycle module."""

from modules.tasks.automation import TaskAutomation
from modules.tasks.execution import TaskExecution

__all__ = ["TaskAutomation", "TaskExecution"]
