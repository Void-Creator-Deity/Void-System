"""HTTP adapter for the Planning Engine."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, status

from api.http.dependencies import get_current_user, get_growth_profile, get_runtime_settings
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.planning import AdvisorRequest, RunPlanRequest
from core.planning_contracts import PlanRequest, UserCapability
from core.runtime_settings import RuntimeSettings
from errors import VoidSystemException
from modules.planning.context import build_generation_context, select_generation_mode
from modules.planning.service import get_planning_engine
from modules.growth.profile import GrowthProfile


logger = logging.getLogger("void-system.planning")
router = APIRouter(tags=["AI服务"])


@router.post(
    "/api/plans",
    summary="生成可审阅的执行方案",
    response_model=APIResponse,
)
async def create_run_plan(
    body: RunPlanRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    profile: GrowthProfile = Depends(get_growth_profile),
    settings: RuntimeSettings = Depends(get_runtime_settings),
) -> APIResponse:
    topic = body.topic.strip()
    try:
        user_attributes = profile.list_capabilities(current_user["user_id"])
        capabilities = [
            UserCapability(
                id=str(attribute.get("attr_id") or ""),
                name=str(attribute.get("attr_name") or ""),
                value=int(attribute.get("attr_value") or 0),
                max_value=int(attribute.get("max_value") or 100),
                description=str(attribute.get("description") or ""),
            )
            for attribute in user_attributes
        ]
        planner_mode = "single_task" if body.max_steps == 1 else "workflow_chain"
        plan = get_planning_engine(settings).plan(
            PlanRequest(
                topic=topic,
                profile_context=build_generation_context(
                    current_user,
                    user_attributes,
                    advisor_preferences=body.advisor_prefs,
                ),
                capabilities=capabilities,
                mode=planner_mode,
                max_steps=body.max_steps,
                strict=False,
            )
        )
        result = _serialize_run_plan(
            plan,
            topic=topic,
            execution_mode=body.execution_mode,
            max_steps=body.max_steps,
        )
        return create_success_response("执行方案已生成，请确认后开始", data=result)
    except VoidSystemException:
        raise
    except ImportError as exc:
        raise VoidSystemException(
            message="规划服务暂时不可用",
            error_code="AI_SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    except Exception as exc:
        logger.error("Run plan generation failed (%s)", type(exc).__name__)
        raise VoidSystemException(
            message="执行方案生成失败",
            error_code="PLANNING_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


@router.post(
    "/api/ai/advisor",
    summary="获取 AI 任务建议",
    response_model=APIResponse,
)
async def get_ai_advisor(
    body: AdvisorRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    profile: GrowthProfile = Depends(get_growth_profile),
    settings: RuntimeSettings = Depends(get_runtime_settings),
) -> APIResponse:
    topic = body.topic.strip()
    if not topic:
        raise VoidSystemException(
            message="主题不能为空",
            error_code="TOPIC_REQUIRED",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_attributes = profile.list_capabilities(current_user["user_id"])
        profile_context = build_generation_context(
            current_user,
            user_attributes,
            advisor_preferences=body.advisor_prefs,
        )
        mode, mode_reason = select_generation_mode(topic)
        if body.force_mode in {"single_task", "workflow_chain"}:
            mode = body.force_mode
            mode_reason = f"forced_by_user:{body.force_mode}"
        elif mode_reason != "explicit_single_keyword":
            mode = "workflow_chain"
            mode_reason = f"auto_default_workflow:{mode_reason}"

        capabilities = [
            UserCapability(
                id=str(attribute.get("attr_id") or ""),
                name=str(attribute.get("attr_name") or ""),
                value=int(attribute.get("attr_value") or 0),
                max_value=int(attribute.get("max_value") or 100),
                description=str(attribute.get("description") or ""),
            )
            for attribute in user_attributes
        ]
        plan = get_planning_engine(settings).plan(
            PlanRequest(
                topic=topic,
                profile_context=profile_context,
                capabilities=capabilities,
                mode=mode,
                strict=False,
            )
        )
        result = _serialize_plan(plan, topic=topic, mode=mode)
        return create_success_response("任务建议生成成功", data=result)
    except VoidSystemException:
        raise
    except ImportError as exc:
        raise VoidSystemException(
            message="AI 服务暂时不可用",
            error_code="AI_SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    except Exception as exc:
        logger.error("Task advice generation failed (%s)", type(exc).__name__)
        raise VoidSystemException(
            message="任务建议生成失败",
            error_code="ADVISOR_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


def _serialize_plan(plan, *, topic: str, mode: str) -> Dict[str, Any]:
    tasks = [_serialize_task(task) for task in plan.tasks]
    if mode == "single_task" and len(tasks) != 1:
        raise VoidSystemException(
            message="规划结果不完整，请重新生成后再发布",
            error_code="ADVISOR_INVALID_PLAN",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if mode == "workflow_chain" and not tasks:
        raise VoidSystemException(
            message="规划结果不完整，请重新生成后再发布",
            error_code="ADVISOR_INVALID_PLAN",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    metadata = plan.metadata if isinstance(plan.metadata, dict) else {}
    return {
        "mode": mode,
        "query": topic,
        "response": str(plan.response or "").strip(),
        "estimated_duration": str(plan.estimated_duration or "").strip(),
        "tasks": tasks,
        "meta": {"fallback": bool(metadata.get("fallback", False))},
    }


def _serialize_task(task: Any) -> Dict[str, Any]:
    title = str(getattr(task, "title", "") or "").strip()
    description = str(getattr(task, "description", "") or "").strip()
    priority = str(getattr(task, "priority", "") or "").strip()
    completion_type = str(getattr(task, "completion_type", "") or "").strip()
    task_type = str(getattr(task, "task_type", "") or "").strip()
    criteria = getattr(task, "completion_criteria", None)
    related_attrs = getattr(task, "related_attrs", None)
    attribute_plan = getattr(task, "attribute_plan", None)

    try:
        estimated_time = int(getattr(task, "estimated_time", 0) or 0)
        reward_coins = int(getattr(task, "reward_coins", 0) or 0)
        attribute_points = int(getattr(task, "attribute_points", 0) or 0)
    except (TypeError, ValueError):
        estimated_time = reward_coins = attribute_points = -1

    is_valid = (
        title
        and description
        and 1 <= estimated_time <= 480
        and 0 <= reward_coins <= 1000
        and 0 <= attribute_points <= 100
        and priority in {"easy", "medium", "hard"}
        and completion_type in {"simple", "progress", "ai_eval", "submission"}
        and task_type in {"main", "side", "daily"}
        and isinstance(criteria, dict)
        and isinstance(related_attrs, dict)
        and isinstance(attribute_plan, list)
    )
    if not is_valid:
        raise VoidSystemException(
            message="规划结果不完整，请重新生成后再发布",
            error_code="ADVISOR_INVALID_PLAN",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    return {
        "title": title,
        "description": description,
        "estimated_time": estimated_time,
        "reward_coins": reward_coins,
        "attribute_points": attribute_points,
        "priority": priority,
        "task_type": task_type,
        "completion_type": completion_type,
        "related_attrs": related_attrs,
        "completion_criteria": criteria,
        "attribute_plan": attribute_plan,
    }


def _serialize_run_plan(
    plan: Any,
    *,
    topic: str,
    execution_mode: str,
    max_steps: int,
) -> Dict[str, Any]:
    tasks = [_serialize_task(task) for task in plan.tasks]
    if not tasks or len(tasks) > max_steps:
        raise VoidSystemException(
            message="规划结果不完整，请调整目标后重新生成",
            error_code="PLANNING_INVALID_RUN_SPEC",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    steps = []
    previous_key = None
    for index, task in enumerate(tasks, start=1):
        key = f"step-{index}"
        steps.append(
            {
                "client_key": key,
                "title": task["title"],
                "description": task["description"],
                "kind": "agent" if execution_mode == "agent" else "manual",
                "depends_on": [previous_key] if previous_key else [],
                "max_attempts": 3 if execution_mode == "agent" else 1,
                "requires_approval": False,
                "completion_criteria": task["completion_criteria"],
                "input_data": {
                    "estimated_minutes": task["estimated_time"],
                    "capability_plan": task["attribute_plan"],
                },
            }
        )
        previous_key = key
    metadata = plan.metadata if isinstance(plan.metadata, dict) else {}
    return {
        "goal": {
            "title": topic[:160],
            "description": str(plan.response or "").strip(),
            "desired_outcome": topic,
            "priority": "medium",
        },
        "run": {
            "title": topic[:160],
            "objective": topic,
            "mode": execution_mode,
            "steps": steps,
        },
        "summary": str(plan.response or "").strip(),
        "estimated_duration": str(plan.estimated_duration or "").strip(),
        "meta": {
            "needs_review": True,
            "used_fallback": bool(metadata.get("fallback", False)),
        },
    }
