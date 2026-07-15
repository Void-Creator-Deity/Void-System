"""Legacy planning adapters wrapping services.ai_services.advisor_chain."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.runtime_settings import RuntimeSettings
from services.ai_services.llm_factory import runtime_settings_scope
from contextlib import nullcontext as _null_context

from core.planning_contracts import (
    EvaluationEngine,
    EvaluationRequest,
    EvaluationResult,
    PlanRequest,
    PlanResult,
    PlannedTask,
    PlanningEngine,
    UserCapability,
)


def _capability_to_legacy(attr: UserCapability) -> Dict[str, Any]:
    return {
        "attr_id": attr.id,
        "attr_name": attr.name,
        "attr_value": attr.value,
        "max_value": attr.max_value,
        "description": attr.description,
    }


def _legacy_step_to_task(step: Dict[str, Any]) -> PlannedTask:
    return PlannedTask(
        title=str(step.get("title") or step.get("task_name") or "").strip(),
        description=str(step.get("description") or ""),
        task_type=str(step.get("task_type") or "main"),
        priority=str(step.get("priority") or "medium"),
        estimated_time=int(step.get("estimated_time") or 30),
        reward_coins=int(step.get("reward_coins") or 20),
        attribute_points=int(step.get("attribute_points") or 0),
        related_attrs=dict(step.get("related_attrs") or {}),
        completion_type=str(step.get("completion_type") or "ai_eval"),
        completion_criteria=dict(step.get("completion_criteria") or {}),
        attribute_plan=list(step.get("attribute_plan") or []),
    )


class LegacyAdvisorPlanningEngine(PlanningEngine):
    """PlanningEngine adapter backed by advisor_chain."""

    def __init__(self, settings: Optional[RuntimeSettings] = None) -> None:
        self._settings = settings

    def plan(self, request: PlanRequest) -> PlanResult:
        from services.ai_services.advisor_chain import generate_single_task, generate_workflow_chain

        legacy_attrs = [_capability_to_legacy(attr) for attr in request.capabilities]
        with runtime_settings_scope(self._settings) if self._settings is not None else _null_context():
            if request.mode == "single_task":
                raw = generate_single_task(
                    request.topic,
                    profile_context=request.profile_context,
                    user_attrs=legacy_attrs,
                )
                steps = [raw]
            else:
                raw = generate_workflow_chain(
                    request.topic,
                    profile_context=request.profile_context,
                    user_attrs=legacy_attrs,
                    allow_fallback=not request.strict,
                )
                steps = raw.get("steps") or []
        return PlanResult(
            response=str(raw.get("response") or "已生成任务计划。"),
            tasks=[_legacy_step_to_task(step) for step in steps],
            mode=str(raw.get("mode") or request.mode),
            estimated_duration=str(raw.get("estimatedDuration") or raw.get("estimated_duration") or "—"),
            raw=raw,
            metadata=dict(raw.get("meta") or {}),
        )


class LegacyTaskEvaluationEngine(EvaluationEngine):
    """EvaluationEngine adapter backed by advisor_chain.evaluate_submission."""

    def __init__(self, settings: Optional[RuntimeSettings] = None) -> None:
        self._settings = settings

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        from services.ai_services.advisor_chain import evaluate_submission

        with runtime_settings_scope(self._settings) if self._settings is not None else _null_context():
            raw = evaluate_submission(request.task, request.submission, request.user_stats)
        return EvaluationResult(
            status=str(raw.get("status") or "fail"),
            feedback=str(raw.get("feedback") or ""),
            score=int(raw.get("score") or 0),
            suggested_rewards=dict(raw.get("suggested_rewards") or {}),
            raw=raw,
        )
