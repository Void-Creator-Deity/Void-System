"""Canonical AI adapters for planning and task-evidence evaluation."""
from __future__ import annotations

from contextlib import nullcontext as _null_context
from typing import Any, Dict, Optional

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
from core.runtime_settings import RuntimeSettings
from services.ai_services.llm_factory import runtime_settings_scope


def _capability_to_planner(attr: UserCapability) -> Dict[str, Any]:
    """Convert a portable capability value into the AI service input shape."""
    return {
        "attr_id": attr.id,
        "attr_name": attr.name,
        "attr_value": attr.value,
        "max_value": attr.max_value,
        "description": attr.description,
    }


def _planner_step_to_task(step: Dict[str, Any]) -> PlannedTask:
    """Normalize one validated AI-service step into the portable result contract."""
    return PlannedTask(
        title=str(step.get("title") or step.get("task_name") or "").strip(),
        description=str(step.get("description") or ""),
        task_type=str(step.get("task_type") or "main"),
        priority=str(step.get("priority") or "medium"),
        estimated_time=int(step.get("estimated_time") or 30),
        reward_growth_points=int(step.get("reward_growth_points") or 20),
        attribute_points=int(step.get("attribute_points") or 0),
        related_attrs=dict(step.get("related_attrs") or {}),
        completion_type=str(step.get("completion_type") or "ai_eval"),
        completion_criteria=dict(step.get("completion_criteria") or {}),
        attribute_plan=list(step.get("attribute_plan") or []),
    )


def build_planning_collaboration_instruction(request: PlanRequest) -> str:
    """Render a bounded, model-facing presentation instruction.

    Inputs: the typed policy embedded in a PlanRequest. Output: prompt text
    passed to the structured-planning call. The text deliberately contains no
    persona brief or permission data, so user-editable profile text cannot
    redefine output format, authorization, or task-execution behavior.
    """
    tone = request.interaction_policy.tone
    initiative = request.interaction_policy.initiative
    tone_instruction = {
        "warm": "Use supportive, encouraging wording while keeping each step concrete.",
        "direct": "Lead with the practical outcome and use concise, decisive wording.",
    }.get(tone, "Use calm, clear, and well-structured wording.")
    initiative_instruction = {
        "quiet": "Do not add suggestions beyond the requested plan.",
        "proactive": "You may add one optional immediate next action in the response summary when it genuinely helps.",
    }.get(initiative, "Keep the response focused; include at most one optional next action when it clearly helps.")
    return (
        "Presentation policy only: "
        f"{tone_instruction} {initiative_instruction} "
        "This policy must not change the required JSON schema, facts, authorization, "
        "execution mode, task state, rewards, completion requirements, or safety boundaries."
    )


class AdvisorPlanningEngine(PlanningEngine):
    """Canonical PlanningEngine adapter backed by the one-pass advisor service."""

    def __init__(self, settings: Optional[RuntimeSettings] = None) -> None:
        self._settings = settings

    def plan(self, request: PlanRequest) -> PlanResult:
        """Generate one normalized plan using the RuntimeSettings snapshot.

        Inputs: a portable PlanRequest. Output: a PlanResult suitable for the
        durable plan-draft publisher. Calls: one of the AI-service planning
        functions inside the configured runtime scope.
        """
        from services.ai_services.advisor_chain import generate_single_task, generate_structured_plan

        planner_attributes = [_capability_to_planner(attr) for attr in request.capabilities]
        collaboration_instruction = build_planning_collaboration_instruction(request)
        with runtime_settings_scope(self._settings) if self._settings is not None else _null_context():
            if request.mode == "single_task":
                raw = generate_single_task(
                    request.topic,
                    profile_context=request.profile_context,
                    user_attrs=planner_attributes,
                    collaboration_instruction=collaboration_instruction,
                )
                steps = [raw]
            else:
                raw = generate_structured_plan(
                    request.topic,
                    profile_context=request.profile_context,
                    user_attrs=planner_attributes,
                    max_steps=request.max_steps,
                    allow_fallback=not request.strict,
                    collaboration_instruction=collaboration_instruction,
                )
                steps = raw.get("steps") or []
        return PlanResult(
            response=str(raw.get("response") or "Plan draft generated."),
            tasks=[_planner_step_to_task(step) for step in steps],
            mode=str(raw.get("mode") or request.mode),
            estimated_duration=str(raw.get("estimatedDuration") or raw.get("estimated_duration") or "To be reviewed"),
            raw=raw,
            metadata=dict(raw.get("meta") or {}),
        )


class TaskEvaluationEngine(EvaluationEngine):
    """Canonical EvaluationEngine adapter backed by the AI evidence evaluator."""

    def __init__(self, settings: Optional[RuntimeSettings] = None) -> None:
        self._settings = settings

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """Evaluate task evidence under the explicit RuntimeSettings snapshot."""
        from services.ai_services.advisor_chain import evaluate_submission

        with runtime_settings_scope(self._settings) if self._settings is not None else _null_context():
            raw = evaluate_submission(request.task, request.submission, request.user_stats)
        return EvaluationResult(
            status=str(raw.get("status") or "fail"),
            feedback=str(raw.get("feedback") or ""),
            score=int(raw.get("score") or 0),
            raw=raw,
        )
