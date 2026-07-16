"""Shared migration metadata for the retired task and task-chain HTTP surface."""
from __future__ import annotations

from typing import Any, Mapping, Optional

LEGACY_TASK_SUNSET = "Fri, 16 Jul 2027 00:00:00 GMT"
LEGACY_TASK_REPLACEMENTS = {
    "goals": "/api/goals",
    "runs": "/api/runs",
    "workspace": "/tasks",
}


def legacy_task_metadata(
    execution_link: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Describe the compatibility adapter without leaking its database implementation."""
    return {
        "deprecated": True,
        "adapter": "legacy-task-execution-projection",
        "replacement": dict(LEGACY_TASK_REPLACEMENTS),
        "canonical": dict(execution_link) if execution_link is not None else None,
    }


def mark_legacy_task_response_headers(response: Any) -> None:
    """Make all legacy task responses self-describing for existing API clients."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = LEGACY_TASK_SUNSET
    response.headers["Link"] = '</api/goals>; rel="successor-version", </api/runs>; rel="successor-version"'
    response.headers["X-Void-Compatibility"] = "legacy-task-execution-projection"
