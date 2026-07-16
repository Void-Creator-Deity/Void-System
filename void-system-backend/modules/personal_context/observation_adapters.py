"""Normalize product events into conservative, reviewable profile evidence."""
from __future__ import annotations

from typing import Any, Mapping, TYPE_CHECKING

from core.personal_context_contracts import PersonalContextRepository
from core.task_execution_contracts import (
    RunReviewMemoryCandidateSink,
    RunReviewObservationSink,
)

if TYPE_CHECKING:
    from modules.personal_context.profile import ProfileCognition


def _review_weight(review: Mapping[str, Any]) -> float:
    rating = review.get("rating")
    if isinstance(rating, int) and 1 <= rating <= 5:
        return {1: 0.45, 2: 0.5, 3: 0.55, 4: 0.65, 5: 0.7}[rating]
    return 0.5


class TaskReviewObservationAdapter(RunReviewObservationSink):
    """Records a stable task-review fact; it never infers a profile claim."""

    def __init__(self, profile: ProfileCognition) -> None:
        self._profile = profile

    def record_run_review(
        self,
        owner_id: str,
        run: Mapping[str, Any],
        review: Mapping[str, Any],
    ) -> None:
        run_id = str(run.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("run review evidence requires a run_id")
        title = " ".join(str(run.get("title") or run.get("goal_title") or "Action").split())
        title = title[:180] or "Action"
        outcome = review.get("outcome")
        rating = review.get("rating")
        detail = []
        if outcome:
            detail.append(str(outcome))
        if rating is not None:
            detail.append(f"rating {rating}/5")
        suffix = f" ({', '.join(detail)})" if detail else ""
        self._profile.upsert_observation(
            owner_id,
            {
                "kind": "task",
                "summary": f"Action review: {title}{suffix}",
                "source_type": "task_run_review",
                "source_ref": f"run:{run_id}:review",
                "attributes": {
                    "run_id": run_id,
                    "goal_id": run.get("goal_id"),
                    "outcome": outcome,
                    "rating": rating,
                    "has_notes": bool(review.get("notes")),
                    "has_next_action": bool(review.get("next_action")),
                },
                "weight": _review_weight(review),
                "observed_at": review.get("updated_at"),
                "sensitivity": "private",
                "status": "active",
            },
        )


class TaskReviewMemoryCandidateAdapter(RunReviewMemoryCandidateSink):
    """Creates owner-scoped, reviewable task-review memory candidates."""

    def __init__(self, repository: PersonalContextRepository) -> None:
        self._repository = repository

    def propose_run_review_memory(
        self,
        owner_id: str,
        run: Mapping[str, Any],
        review: Mapping[str, Any],
    ) -> None:
        run_id = str(run.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("run review memory requires a run_id")
        source_ref = f"run:{run_id}:review"
        existing = self._repository.find_memory_by_source(
            owner_id, "task_run_review", source_ref
        )
        outcome = " ".join(str(review.get("outcome") or "").split())
        rating = review.get("rating")
        has_notes = bool(str(review.get("notes") or "").strip())
        has_next_action = bool(str(review.get("next_action") or "").strip())
        if not (outcome or rating is not None or has_notes or has_next_action):
            if existing and existing.get("review_status") == "pending":
                self._repository.update_memory(
                    owner_id,
                    str(existing["memory_id"]),
                    {"status": "archived", "use_in_context": False},
                )
            return

        title = " ".join(
            str(run.get("title") or run.get("goal_title") or "Action").split()
        )[:135] or "Action"
        details = ["Review recorded for this action"]
        if outcome:
            details.append(f"outcome: {outcome[:30]}")
        if rating is not None:
            details.append(f"rating: {rating}/5")
        if has_notes:
            details.append("a reflection note was provided")
        if has_next_action:
            details.append("a next action was identified")
        values = {
            "memory_type": "episode",
            "title": f"Task review: {title}"[:160],
            "content": "; ".join(details)[:4000],
            "source_type": "task_run_review",
            "source_ref": source_ref,
            "confidence": _review_weight(review),
            "use_in_context": False,
            "status": "active",
            "review_status": "pending",
            "evidence_refs": [{"type": "task_run_review", "id": run_id}],
            "review_note": "",
            "reviewed_at": None,
            "expires_at": None,
            "metadata": {
                "candidate_kind": "task_review",
                "goal_id": run.get("goal_id"),
                "contribute_to_profile": False,
            },
        }
        if existing is None:
            self._repository.create_memory(owner_id, values)
            return
        if existing.get("review_status") != "pending":
            return
        self._repository.update_memory(owner_id, str(existing["memory_id"]), values)
