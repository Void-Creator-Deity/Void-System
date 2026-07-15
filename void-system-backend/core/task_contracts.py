"""Portable contracts for task lifecycle and reward settlement."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence


VALID_TASK_STATUSES = frozenset({
    "pending", "in_progress", "completed", "failed", "pending_evaluation",
})


class TaskWorkflowError(Exception):
    """Expected task workflow failure that can be mapped by any transport."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class RewardGrant:
    coins: int
    experience: int
    attribute_increments: Dict[str, int] = field(default_factory=dict)
    source: str = "task_completion"


@dataclass(frozen=True)
class CompletionResult:
    task_id: str
    status: str
    reward_granted: bool
    reward: Optional[RewardGrant] = None


@dataclass(frozen=True)
class TaskEvaluationOutcome:
    status: str
    feedback: str
    score: int
    suggested_rewards: Dict[str, int] = field(default_factory=dict)
    reward_granted: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)


class TaskRepository(Protocol):
    """Persistence seam required by the task workflow module."""

    def get_task(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]: ...
    def list_tasks(self, user_id: str) -> Sequence[Dict[str, Any]]: ...
    def list_attributes(self, user_id: str) -> List[Dict[str, Any]]: ...
    def update_status(self, user_id: str, task_id: str, status: str) -> bool: ...
    def submit_proof(self, user_id: str, task_id: str, proof: Dict[str, Any]) -> bool: ...

    def update_evaluation(
        self,
        user_id: str,
        task_id: str,
        *,
        self_evaluation: Optional[Dict[str, Any]] = None,
        ai_suggestion: Optional[Dict[str, Any]] = None,
    ) -> bool: ...

    def settle_completion(
        self,
        user_id: str,
        task_id: str,
        reward: RewardGrant,
        *,
        ai_suggestion: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Atomically complete and reward once; True means a new grant."""
        ...
