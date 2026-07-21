"""Collect conservative, first-party profile evidence from workspace history."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from core.personal_context_contracts import TaskBehaviorInsightSource
from modules.personal_context.profile import ProfileCognition


class ProfileEvidenceCollector:
    """Project task aggregates into idempotent, reviewable profile signals.

    Inputs:
        tasks: Read-only aggregate task history source. It must not expose task text,
            review notes, artifacts, or other arbitrary user content to this module.
        profile: Canonical profile signal writer.
    Outputs:
        collect returns the signals inserted or refreshed for one owner.
    Called by:
        PersonalContext.infer_profile_hypotheses after profile consent has been checked.
    Side effects:
        Upserts a small fixed set of aggregate signals with stable source keys.
    Privacy:
        Uses first-party numeric metadata only. It never reads conversations, document
        bodies, raw review notes, artifacts, or external-platform activity.
    """

    _SOURCE_TYPE = "workspace_history_summary"

    def __init__(self, tasks: TaskBehaviorInsightSource, profile: ProfileCognition) -> None:
        self._tasks = tasks
        self._profile = profile

    def collect(self, owner_id: str) -> Sequence[Dict[str, Any]]:
        """Refresh meaningful profile evidence derived from an owner's task aggregates.

        Input:
            owner_id: The only owner whose aggregate records may be read and written.
        Output:
            The canonical signals that met their conservative collection threshold.
        Called by:
            PersonalContext just before it selects safe evidence for a model request.
        Idempotency:
            Each category has a versioned source_ref, so repeated collection updates one
            row instead of accumulating duplicate evidence records.
        """
        signal = self._tasks.summarize_profile_behavior(owner_id)
        if not isinstance(signal, Mapping):
            return []
        signals: list[Dict[str, Any]] = []
        for values in self._candidate_signals(signal):
            signals.append(self._profile.upsert_signal(owner_id, values))
        return signals

    def _candidate_signals(self, signal: Mapping[str, Any]) -> Sequence[Dict[str, Any]]:
        """Build factual aggregate signals without drawing personality conclusions.

        Input:
            signal: Numeric task-history aggregate supplied by Task Execution.
        Output:
            A deterministic ordered sequence suitable for ProfileCognition.upsert_signal.
        Called by:
            collect.
        """
        goals = _count(signal, "goal_count")
        runs = _count(signal, "run_count")
        completed_runs = _count(signal, "completed_run_count")
        cancelled_runs = _count(signal, "cancelled_run_count")
        # Read the legacy key only for aggregate signals saved before the task-mode migration.
        # New Task Execution summaries expose assisted_run_count exclusively.
        assisted_runs = _count(signal, "assisted_run_count")
        if "assisted_run_count" not in signal:
            assisted_runs = _count(signal, "agent_run_count")
        steps = _count(signal, "step_count")
        finished_steps = _count(signal, "finished_step_count")
        reviews = _count(signal, "review_count")
        reviews_with_next_action = _count(signal, "review_with_next_action_count")
        pauses = _count(signal, "pause_count")
        resumes = _count(signal, "resume_count")
        retries = _count(signal, "retry_count")
        refinements = _count(signal, "goal_plan_refinement_count")
        refined_goals = _count(signal, "refined_goal_count")
        candidates: list[Dict[str, Any]] = []

        if goals >= 3:
            candidates.append(self._signal(
                source_ref="task_goals:v1",
                summary=f"已记录该用户创建的 {goals} 个目标。",
                attributes={"goal_count": goals},
                observed_at=_range_end(signal, "goals"),
                weight=0.72,
            ))
        if runs >= 3:
            candidates.append(self._signal(
                source_ref="task_runs:v1",
                summary=(
                    f"已记录 {runs} 次执行尝试，其中 {completed_runs} 次完成、"
                    f"{cancelled_runs} 次取消、{assisted_runs} 次使用协助。"
                ),
                attributes={
                    "run_count": runs,
                    "completed_run_count": completed_runs,
                    "cancelled_run_count": cancelled_runs,
                    "assisted_run_count": assisted_runs,
                },
                observed_at=_range_end(signal, "runs"),
                weight=0.8,
            ))
        if steps >= 6:
            candidates.append(self._signal(
                source_ref="task_steps:v1",
                summary=(
                    f"已记录 {steps} 个计划步骤，其中 {finished_steps} 个已完成或跳过。"
                ),
                attributes={"step_count": steps, "finished_step_count": finished_steps},
                observed_at=_range_end(signal, "steps"),
                weight=0.8,
            ))
        if reviews >= 1:
            candidates.append(self._signal(
                source_ref="task_reviews:v1",
                summary=(
                    f"已记录 {reviews} 次任务复盘，其中 {reviews_with_next_action} 次留下后续行动。"
                ),
                attributes={
                    "review_count": reviews,
                    "review_with_next_action_count": reviews_with_next_action,
                },
                observed_at=_range_end(signal, "reviews"),
                weight=0.76,
            ))
        if pauses + retries >= 2 and resumes + retries >= 1:
            candidates.append(self._signal(
                source_ref="task_recovery:v1",
                summary=(
                    f"已记录 {pauses} 次暂停、{resumes} 次恢复和 {retries} 次重试。"
                ),
                attributes={"pause_count": pauses, "resume_count": resumes, "retry_count": retries},
                observed_at=_latest_range_end(signal, "pauses", "resumes"),
                weight=0.68,
            ))
        if refinements >= 2 and refined_goals >= 1:
            candidates.append(self._signal(
                source_ref="goal_refinements:v1",
                summary=(
                    f"已记录 {refinements} 次计划调整，涉及 {refined_goals} 个目标。"
                ),
                attributes={
                    "goal_plan_refinement_count": refinements,
                    "refined_goal_count": refined_goals,
                },
                observed_at=_range_end(signal, "goal_plan_refinements"),
                weight=0.7,
            ))
        return candidates

    def _signal(
        self,
        *,
        source_ref: str,
        summary: str,
        attributes: Mapping[str, int],
        observed_at: Optional[str],
        weight: float,
    ) -> Dict[str, Any]:
        """Return one normalized signal payload for ProfileCognition.

        Input:
            source_ref: Versioned deterministic identity for this aggregate category.
            summary and attributes: Non-sensitive metadata-only evidence.
        Output:
            A payload accepted by ProfileCognition.upsert_signal.
        Called by:
            _candidate_signals.
        """
        return {
            "kind": "task",
            "summary": summary,
            "source_type": self._SOURCE_TYPE,
            "source_ref": source_ref,
            "attributes": dict(attributes),
            "weight": weight,
            "observed_at": observed_at,
            "sensitivity": "private",
            "status": "active",
        }


def _count(signal: Mapping[str, Any], key: str) -> int:
    """Normalize a non-negative aggregate count without propagating malformed values."""
    try:
        return max(0, int(signal.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def _range_end(signal: Mapping[str, Any], key: str) -> Optional[str]:
    """Return one safe aggregate range endpoint, never a task title or user-entered value."""
    ranges = signal.get("signal_ranges")
    if not isinstance(ranges, Mapping):
        return None
    value = ranges.get(key)
    if not isinstance(value, Mapping):
        return None
    observed_at = value.get("observed_to")
    return str(observed_at) if observed_at else None


def _latest_range_end(signal: Mapping[str, Any], *keys: str) -> Optional[str]:
    """Return the newest timestamp across named aggregate ranges."""
    timestamps = [timestamp for key in keys if (timestamp := _range_end(signal, key))]
    return max(timestamps) if timestamps else None
