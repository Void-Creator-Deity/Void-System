"""HTTP adapter for the Task Workflow module."""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from api.http.dependencies import get_ai_task_workflow, get_current_user, get_task_workflow
from api.http.responses import APIResponse
from api.http.schemas.tasks import AIEvaluateRequest
from core.task_contracts import TaskWorkflowError
from errors import VoidSystemException
from modules.tasks.workflow import TaskWorkflow


logger = logging.getLogger("void-system.tasks")
router = APIRouter(tags=["任务"])


def _translate_workflow_error(exc: TaskWorkflowError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.put(
    "/api/tasks/{task_id}/status",
    summary="更新任务状态",
    response_model=APIResponse,
)
async def update_task_status(
    task_id: str,
    target_status: Optional[str] = Query(None, alias="status"),
    new_status: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow: TaskWorkflow = Depends(get_task_workflow),
) -> APIResponse:
    try:
        result = workflow.change_status(
            current_user["user_id"],
            task_id,
            target_status or new_status or "",
        )
    except TaskWorkflowError as exc:
        raise _translate_workflow_error(exc) from exc

    return APIResponse(
        success=True,
        message="任务状态更新成功",
        data={"status": result.status, "reward_granted": result.reward_granted},
    )


@router.post(
    "/api/tasks/{task_id}/proof",
    summary="提交任务证明",
    response_model=APIResponse,
)
async def submit_task_proof(
    task_id: str,
    proof_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow: TaskWorkflow = Depends(get_task_workflow),
) -> APIResponse:
    try:
        workflow.submit_proof(
            current_user["user_id"],
            task_id,
            proof_data,
        )
    except TaskWorkflowError as exc:
        raise _translate_workflow_error(exc) from exc
    return APIResponse(success=True, message="任务证明提交成功")


@router.post(
    "/api/tasks/{task_id}/evaluate",
    summary="评估任务",
    response_model=APIResponse,
)
async def evaluate_task(
    task_id: str,
    evaluation_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow: TaskWorkflow = Depends(get_task_workflow),
) -> APIResponse:
    try:
        workflow.record_evaluation(
            current_user["user_id"],
            task_id,
            self_evaluation=evaluation_data.get("self_evaluation"),
            ai_suggestion=evaluation_data.get("ai_suggestion"),
        )
    except TaskWorkflowError as exc:
        raise _translate_workflow_error(exc) from exc
    return APIResponse(success=True, message="任务评估更新成功")


@router.post(
    "/api/tasks/{task_id}/ai-evaluate",
    summary="AI 自动评判任务",
    response_model=APIResponse,
)
async def ai_evaluate_task(
    task_id: str,
    req: AIEvaluateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workflow: TaskWorkflow = Depends(get_ai_task_workflow),
) -> APIResponse:
    try:
        outcome = workflow.evaluate_submission(
            user_id=current_user["user_id"],
            task_id=task_id,
            submission=req.submission,
            media_urls=req.media_urls or [],
        )
    except TaskWorkflowError as exc:
        logger.warning("任务 AI 评估未完成: %s (%s)", exc.message, exc.code)
        raise _translate_workflow_error(exc) from exc

    result = dict(outcome.raw)
    result["reward_granted"] = outcome.reward_granted
    return APIResponse(success=True, message="AI 评估完成", data=result)
