"""Conservative, explainable suggestions derived from a user's own task history."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from core.personal_context_contracts import (
    KnowledgeBehaviorInsightSource,
    TaskBehaviorInsightSource,
)


class BehaviorInsightEngine:
    """Turn aggregate execution patterns into reviewable suggestions, never final traits."""

    def __init__(
        self,
        tasks: TaskBehaviorInsightSource,
        knowledge: Optional[KnowledgeBehaviorInsightSource] = None,
    ) -> None:
        self._tasks = tasks
        self._knowledge = knowledge

    def suggest(self, owner_id: str) -> Sequence[Dict[str, Any]]:
        signal = self._tasks.summarize_profile_behavior(owner_id)
        ranges = signal.get("observation_ranges") or {}
        suggestions: list[Dict[str, Any]] = []
        runs = int(signal.get("run_count") or 0)
        completed = int(signal.get("completed_run_count") or 0)
        reviews = int(signal.get("review_count") or 0)
        next_actions = int(signal.get("review_with_next_action_count") or 0)
        paused = int(signal.get("pause_count") or 0)
        resumed = int(signal.get("resume_count") or 0)
        step_count = int(signal.get("step_count") or 0)
        finished_steps = int(signal.get("finished_step_count") or 0)
        approval_count = int(signal.get("approval_count") or 0)
        approved_approvals = int(signal.get("approved_approval_count") or 0)
        plan_refinements = int(signal.get("goal_plan_refinement_count") or 0)
        refined_goals = int(signal.get("refined_goal_count") or 0)

        if reviews >= 3 and next_actions / reviews >= 0.67:
            suggestions.append(self._suggestion(
                key="follow_up_after_review",
                summary="You often turn a completed action into a concrete next step.",
                rationale=(
                    f"{next_actions} of {reviews} action reviews include a next action. "
                    "This is a behavior pattern from your own reviews, not a fixed personal label."
                ),
                confidence=0.72,
                evidence={
                    "signal": "task_review_next_action_rate",
                    "review_count": reviews,
                    "review_with_next_action_count": next_actions,
                },
                observation_range=ranges.get("reviews"),
            ))
        if runs >= 3 and step_count >= 6 and finished_steps / step_count >= 0.65:
            suggestions.append(self._suggestion(
                key="structured_action_planning",
                summary="Your actions tend to progress through multi-step plans.",
                rationale=(
                    f"Your runs contain {step_count} steps, with {finished_steps} finished, "
                    f"across {runs} action attempts."
                ),
                confidence=0.68,
                evidence={
                    "signal": "task_step_completion_pattern",
                    "run_count": runs,
                    "step_count": step_count,
                    "finished_step_count": finished_steps,
                },
                observation_range=_combine_ranges(ranges.get("runs"), ranges.get("steps")),
            ))
        if paused >= 2 and resumed >= 2 and resumed / paused >= 0.6:
            suggestions.append(self._suggestion(
                key="resume_after_pause",
                summary="When you pause an action, you often come back and resume it.",
                rationale=(
                    f"Your action history contains {paused} pauses and {resumed} resumes. "
                    "This only describes the recorded workflow pattern."
                ),
                confidence=0.64,
                evidence={
                    "signal": "task_pause_resume_pattern",
                    "pause_count": paused,
                    "resume_count": resumed,
                },
                observation_range=_combine_ranges(ranges.get("pauses"), ranges.get("resumes")),
            ))
        if runs >= 4 and completed / runs >= 0.7:
            suggestions.append(self._suggestion(
                key="goal_follow_through",
                summary="Your recorded action attempts usually reach completion.",
                rationale=(
                    f"{completed} of {runs} recorded action attempts are completed. "
                    "This is a system-history signal and can change as you use the workspace."
                ),
                confidence=0.7,
                evidence={
                    "signal": "task_run_completion_rate",
                    "run_count": runs,
                    "completed_run_count": completed,
                },
                observation_range=ranges.get("runs"),
            ))
        if approval_count >= 3 and approved_approvals / approval_count >= 0.75:
            suggestions.append(self._suggestion(
                key="approve_after_review",
                summary="Your recorded approval decisions usually let an action continue.",
                rationale=(
                    f"{approved_approvals} of {approval_count} recorded approval decisions were approvals. "
                    "This describes the workflow decisions you recorded, not a preference the system assumes."
                ),
                confidence=0.62,
                evidence={
                    "signal": "task_approval_decision_rate",
                    "approval_count": approval_count,
                    "approved_approval_count": approved_approvals,
                },
                observation_range=ranges.get("approvals"),
            ))
        if plan_refinements >= 3 and refined_goals >= 2:
            suggestions.append(self._suggestion(
                key="refine_goals_during_work",
                summary="You sometimes refine a goal while shaping its plan.",
                rationale=(
                    f"You made {plan_refinements} recorded planning refinements across {refined_goals} goals while shaping them. "
                    "Only the change categories were counted; goal text and notes were not used."
                ),
                confidence=0.6,
                evidence={
                    "signal": "goal_plan_refinement_pattern",
                    "goal_plan_refinement_count": plan_refinements,
                    "refined_goal_count": refined_goals,
                },
                observation_range=ranges.get("goal_plan_refinements"),
            ))
        if self._knowledge is not None:
            knowledge_signal = self._knowledge.summarize_profile_knowledge_use(owner_id)
            reliable_uses = int(knowledge_signal.get("reliable_use_count") or 0)
            total_uses = int(knowledge_signal.get("knowledge_use_count") or 0)
            if reliable_uses >= 4 and reliable_uses / max(total_uses, 1) >= 0.6:
                suggestions.append(self._knowledge_suggestion(
                    reliable_uses=reliable_uses,
                    total_uses=total_uses,
                    observation_range=knowledge_signal.get("observation_range"),
                ))
        return suggestions

    @staticmethod
    def _suggestion(
        *,
        key: str,
        summary: str,
        rationale: str,
        confidence: float,
        evidence: Mapping[str, Any],
        observation_range: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        observed_from, observed_to = _normalized_range(observation_range)
        evidence_data = dict(evidence)
        evidence_data["observed_from"] = observed_from
        evidence_data["observed_to"] = observed_to
        return {
            "suggestion_id": f"task_behavior:{key}",
            "domain": "working_style",
            "profile_key": f"behavior:{key}",
            "summary": summary,
            "value": {
                "kind": "task_behavior",
                "pattern": key,
                "label": summary,
            },
            "rationale": rationale,
            "confidence": confidence,
            "review_status": "pending",
            "first_observed_at": observed_from,
            "last_observed_at": observed_to,
            "evidence_refs": [{"type": "task_behavior_summary", "data": evidence_data}],
            "source": "your_action_history",
            "action": "review_required",
        }


    @staticmethod
    def _knowledge_suggestion(
        *,
        reliable_uses: int,
        total_uses: int,
        observation_range: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        observed_from, observed_to = _normalized_range(observation_range)
        evidence = {
            "signal": "knowledge_supported_use_pattern",
            "knowledge_use_count": total_uses,
            "reliable_use_count": reliable_uses,
            "observed_from": observed_from,
            "observed_to": observed_to,
        }
        return {
            "suggestion_id": "knowledge_behavior:evidence_backed_reference",
            "domain": "working_style",
            "profile_key": "behavior:evidence_backed_reference",
            "summary": "Your saved materials are becoming a repeatable part of your workflow.",
            "value": {
                "kind": "knowledge_behavior",
                "pattern": "evidence_backed_reference",
                "label": "Uses saved materials as a recurring work reference",
            },
            "rationale": (
                f"{reliable_uses} of {total_uses} recorded knowledge uses returned a "
                "supported answer with one or more sources. This describes only how "
                "your saved materials have been used in this workspace."
            ),
            "confidence": 0.66,
            "review_status": "pending",
            "first_observed_at": observed_from,
            "last_observed_at": observed_to,
            "evidence_refs": [{"type": "knowledge_use_summary", "data": evidence}],
            "source": "your_knowledge_use_history",
            "action": "review_required",
        }


def _normalized_range(value: Optional[Mapping[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(value, Mapping):
        return None, None
    observed_from = value.get("observed_from")
    observed_to = value.get("observed_to")
    return (
        str(observed_from) if observed_from else None,
        str(observed_to) if observed_to else None,
    )


def _combine_ranges(*values: Optional[Mapping[str, Any]]) -> Dict[str, Optional[str]]:
    starts: list[str] = []
    ends: list[str] = []
    for value in values:
        observed_from, observed_to = _normalized_range(value)
        if observed_from:
            starts.append(observed_from)
        if observed_to:
            ends.append(observed_to)
    return {
        "observed_from": min(starts) if starts else None,
        "observed_to": max(ends) if ends else None,
    }
