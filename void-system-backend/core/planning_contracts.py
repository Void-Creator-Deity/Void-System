"""Portable contracts for the canonical planning and evaluation boundary.

Plan Generation depends on these value types rather than an HTTP route, database
schema, or a particular model SDK. A future deterministic or multi-agent engine
can replace the active adapter without changing durable jobs or route handlers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence


@dataclass(frozen=True)
class UserCapability:
    """A user skill/attribute available to planning and reward allocation."""

    id: str
    name: str
    value: int = 0
    max_value: int = 100
    description: str = ""


@dataclass(frozen=True)
class PlanningInteractionPolicy:
    """Bounded wording preferences for a planning response.

    Inputs: server-normalized companion settings. Outputs: enum-like values
    consumed by the planning adapter. This object never carries persona text,
    permissions, execution mode, or other user-authored instruction content.
    """

    tone: str = "calm"
    initiative: str = "balanced"


@dataclass(frozen=True)
class PlanRequest:
    """Request to turn a user goal into one task or a task group.

    The interaction policy can affect plan explanation and the optional next
    action only. It cannot change the output schema, task state, authorization,
    rewards, or other execution semantics.
    """

    topic: str
    profile_context: str = ""
    capabilities: Sequence[UserCapability] = field(default_factory=list)
    mode: str = "auto"
    max_steps: int = 8
    strict: bool = False
    interaction_policy: PlanningInteractionPolicy = field(
        default_factory=PlanningInteractionPolicy
    )


@dataclass(frozen=True)
class PlannedTask:
    """Portable task proposal independent of storage schema."""

    title: str
    description: str
    task_type: str = "main"
    priority: str = "medium"
    estimated_time: int = 30
    reward_growth_points: int = 20
    attribute_points: int = 0
    related_attrs: Dict[str, float] = field(default_factory=dict)
    completion_type: str = "ai_eval"
    completion_criteria: Dict[str, Any] = field(default_factory=dict)
    attribute_plan: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class PlanResult:
    """Planner output with enough metadata for review and publishing."""

    response: str
    tasks: Sequence[PlannedTask]
    mode: str
    estimated_duration: str = "—"
    raw: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationRequest:
    """Request to evaluate user evidence for a task."""

    task: Dict[str, Any]
    submission: Dict[str, Any]
    user_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationResult:
    """Normalized task evaluation result; rewards are fixed before execution."""

    status: str
    feedback: str
    score: int
    raw: Dict[str, Any] = field(default_factory=dict)


class PlanningEngine(Protocol):
    """Adapter interface for goal-to-task planning."""

    def plan(self, request: PlanRequest) -> PlanResult:
        """Generate a task plan from a goal."""


class EvaluationEngine(Protocol):
    """Adapter interface for task completion evaluation."""

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """Evaluate whether a task is complete."""
