"""Portable contracts for durable Goal and Run execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence


GOAL_STATUSES = frozenset({"active", "completed", "archived"})
RUN_STATUSES = frozenset({
    "queued", "running", "paused", "waiting_approval", "completed", "failed", "cancelled",
})
RUN_MODES = frozenset({"manual", "assisted"})
STEP_STATUSES = frozenset({
    "pending", "ready", "running", "waiting_approval", "completed", "failed", "skipped", "cancelled",
})
STEP_KINDS = frozenset({"manual"})
TERMINAL_RUN_STATUSES = frozenset({"completed", "failed", "cancelled"})
TERMINAL_STEP_STATUSES = frozenset({"completed", "failed", "skipped", "cancelled"})
SATISFIED_STEP_STATUSES = frozenset({"completed", "skipped"})


class TaskExecutionError(Exception):
    """Expected Task Execution failure that transports can translate."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class StepSpec:
    title: str
    description: str = ""
    kind: str = "manual"
    depends_on: Sequence[str] = field(default_factory=tuple)
    parallel_group: Optional[str] = None
    max_attempts: int = 1
    requires_approval: bool = False
    completion_criteria: Mapping[str, Any] = field(default_factory=dict)
    input_data: Mapping[str, Any] = field(default_factory=dict)
    # A bounded, publication-time declaration. Completion never asks a model to price work.
    reward_spec: Mapping[str, Any] = field(default_factory=dict)
    client_key: Optional[str] = None


class RunReviewObservationSink(Protocol):
    """Receives noncritical evidence derived from a saved Run review."""

    def record_run_review(
        self,
        owner_id: str,
        run: Mapping[str, Any],
        review: Mapping[str, Any],
    ) -> None: ...


class RunReviewMemoryCandidateSink(Protocol):
    """Proposes reviewable memory without changing Run review durability."""

    def propose_run_review_memory(
        self,
        owner_id: str,
        run: Mapping[str, Any],
        review: Mapping[str, Any],
    ) -> None: ...


class TaskExecutionRepository(Protocol):
    """Persistence Interface required by the Task Execution Module."""

    def create_goal(self, user_id: str, values: Mapping[str, Any]) -> Dict[str, Any]: ...
    def list_goals(self, user_id: str, status: Optional[str] = None) -> Sequence[Dict[str, Any]]: ...
    def get_goal(self, user_id: str, goal_id: str) -> Optional[Dict[str, Any]]: ...
    def update_goal(self, user_id: str, goal_id: str, values: Mapping[str, Any]) -> bool: ...

    def create_run(
        self,
        user_id: str,
        goal_id: str,
        values: Mapping[str, Any],
        steps: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]: ...
    def list_runs(
        self,
        user_id: str,
        *,
        goal_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Sequence[Dict[str, Any]]: ...
    def get_run(self, user_id: str, run_id: str) -> Optional[Dict[str, Any]]: ...
    def summarize_profile_behavior(self, user_id: str) -> Dict[str, Any]: ...
    def compare_and_set_run_status(
        self,
        user_id: str,
        run_id: str,
        expected: Sequence[str],
        target: str,
        *,
        error_summary: Optional[str] = None,
    ) -> bool: ...
    def compare_and_set_step_status(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        expected: Sequence[str],
        target: str,
        *,
        output_data: Optional[Mapping[str, Any]] = None,
        error_summary: Optional[str] = None,
        increment_attempt: bool = False,
    ) -> bool: ...

    def apply_run_transition(
        self,
        user_id: str,
        run_id: str,
        expected: Sequence[str],
        target: str,
        event_type: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
        error_summary: Optional[str] = None,
        cancel_open_steps: bool = False,
        publish_ready_steps: bool = False,
    ) -> bool: ...
    def apply_step_transition(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        expected: Sequence[str],
        target: str,
        event_type: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
        output_data: Optional[Mapping[str, Any]] = None,
        error_summary: Optional[str] = None,
        increment_attempt: bool = False,
        artifacts: Sequence[Mapping[str, Any]] = (),
        publish_ready_steps: bool = False,
        run_expected: Sequence[str] = (),
        run_target: Optional[str] = None,
        run_event_type: Optional[str] = None,
        run_payload: Optional[Mapping[str, Any]] = None,
        run_error_summary: Optional[str] = None,
        complete_run_if_satisfied: bool = False,
    ) -> Dict[str, Any]: ...
    def mark_ready_steps(self, user_id: str, run_id: str) -> Sequence[str]: ...
    def cancel_open_steps(self, user_id: str, run_id: str) -> None: ...

    def append_event(
        self,
        user_id: str,
        run_id: str,
        event_type: str,
        *,
        step_id: Optional[str] = None,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]: ...
    def list_events(self, user_id: str, run_id: str) -> Sequence[Dict[str, Any]]: ...

    def get_run_review(self, user_id: str, run_id: str) -> Optional[Dict[str, Any]]: ...
    def upsert_run_review(
        self,
        user_id: str,
        run_id: str,
        values: Mapping[str, Any],
    ) -> Dict[str, Any]: ...
    def list_run_reward_settlements(
        self, user_id: str, run_id: str
    ) -> Sequence[Dict[str, Any]]: ...

    def create_action(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        values: Mapping[str, Any],
    ) -> Dict[str, Any]: ...
    def complete_action(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        action_id: str,
        status: str,
        *,
        output_data: Optional[Mapping[str, Any]] = None,
        error_summary: Optional[str] = None,
    ) -> bool: ...

    def create_artifact(
        self,
        user_id: str,
        run_id: str,
        values: Mapping[str, Any],
        *,
        step_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...
    def create_approval(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        request: Mapping[str, Any],
    ) -> Dict[str, Any]: ...
    def get_approval(self, user_id: str, approval_id: str) -> Optional[Dict[str, Any]]: ...
    def resolve_approval(
        self,
        user_id: str,
        approval_id: str,
        decision: str,
        note: Optional[str],
    ) -> bool: ...

    def request_approval_transition(
        self,
        user_id: str,
        run_id: str,
        step_id: str,
        expected_step_status: str,
        request: Mapping[str, Any],
    ) -> Optional[Dict[str, Any]]: ...
    def resolve_approval_transition(
        self,
        user_id: str,
        approval_id: str,
        decision: str,
        note: Optional[str],
    ) -> Optional[str]: ...
