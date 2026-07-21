"""HTTP Adapter for durable Goal and Run execution."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from api.http.dependencies import get_current_user, get_task_execution
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.task_execution import (
    ActionCompleteRequest,
    ActionStartRequest,
    ApprovalDecisionRequest,
    ApprovalRequest,
    GoalCreate,
    GoalUpdate,
    RunCancelRequest,
    RunCreate,
    RunReviewUpdate,
    AssistedStepReviewRequest,
    StepCompleteRequest,
    StepFailRequest,
)
from core.task_execution_contracts import TaskExecutionError
from errors import VoidSystemException
from modules.tasks.execution import TaskExecution


router = APIRouter(tags=["任务执行"])


def _translate_error(exc: TaskExecutionError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.post("/api/goals", summary="创建目标", response_model=APIResponse)
async def create_goal(
    request: GoalCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        goal = execution.create_goal(current_user["user_id"], request.model_dump())
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("目标已创建", {"goal": goal})


@router.get("/api/goals", summary="获取目标列表", response_model=APIResponse)
async def list_goals(
    status: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        goals = execution.list_goals(current_user["user_id"], status)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("目标列表已更新", {"goals": goals})


@router.get("/api/goals/{goal_id}", summary="获取目标详情", response_model=APIResponse)
async def get_goal(
    goal_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        goal = execution.get_goal(current_user["user_id"], goal_id)
        runs = execution.list_runs(current_user["user_id"], goal_id=goal_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("目标详情已更新", {"goal": goal, "runs": runs})


@router.patch("/api/goals/{goal_id}", summary="更新目标", response_model=APIResponse)
async def update_goal(
    goal_id: str,
    request: GoalUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        goal = execution.update_goal(
            current_user["user_id"], goal_id, request.model_dump(exclude_unset=True)
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("目标已更新", {"goal": goal})


@router.post("/api/goals/{goal_id}/runs", summary="创建执行记录", response_model=APIResponse)
async def create_run(
    goal_id: str,
    request: RunCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.create_run(current_user["user_id"], goal_id, request.model_dump())
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行记录已创建", {"run": run})


@router.get("/api/runs", summary="获取执行记录", response_model=APIResponse)
async def list_runs(
    goal_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        runs = execution.list_runs(
            current_user["user_id"], goal_id=goal_id, status=status
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行记录已更新", {"runs": runs})


@router.get("/api/runs/{run_id}", summary="获取执行详情", response_model=APIResponse)
async def get_run(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.get_run(current_user["user_id"], run_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行详情已更新", {"run": run})


@router.get("/api/runs/{run_id}/review", summary="查看行动复盘", response_model=APIResponse)
async def get_run_review(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        review = execution.get_run_review(current_user["user_id"], run_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("行动复盘已更新", {"review": review})


@router.put("/api/runs/{run_id}/review", summary="记录行动复盘", response_model=APIResponse)
async def update_run_review(
    run_id: str,
    request: RunReviewUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        review = execution.update_run_review(
            current_user["user_id"], run_id, request.model_dump(exclude_unset=True)
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("行动复盘已保存", {"review": review})


@router.get("/api/runs/{run_id}/events", summary="获取执行时间线", response_model=APIResponse)
async def list_run_events(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        events = execution.list_events(current_user["user_id"], run_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行时间线已更新", {"events": events})


@router.post("/api/runs/{run_id}/start", summary="开始执行", response_model=APIResponse)
async def start_run(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.start_run(current_user["user_id"], run_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行已开始", {"run": run})


@router.post("/api/runs/{run_id}/pause", summary="暂停执行", response_model=APIResponse)
async def pause_run(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.pause_run(current_user["user_id"], run_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行已暂停", {"run": run})


@router.post("/api/runs/{run_id}/resume", summary="继续执行", response_model=APIResponse)
async def resume_run(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.resume_run(current_user["user_id"], run_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行已继续", {"run": run})


@router.post("/api/runs/{run_id}/cancel", summary="取消执行", response_model=APIResponse)
async def cancel_run(
    run_id: str,
    request: RunCancelRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.cancel_run(current_user["user_id"], run_id, request.reason)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行已取消", {"run": run})


@router.post("/api/runs/{run_id}/retry", summary="重新开始执行", response_model=APIResponse)
async def retry_run(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.retry_run(current_user["user_id"], run_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行已重新开始", {"run": run})


@router.post("/api/runs/{run_id}/steps/{step_id}/start", summary="开始步骤", response_model=APIResponse)
async def start_step(
    run_id: str,
    step_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.start_step(current_user["user_id"], run_id, step_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("步骤已开始", {"run": run})


@router.post("/api/runs/{run_id}/steps/{step_id}/skip", summary="跳过步骤", response_model=APIResponse)
async def skip_step(
    run_id: str,
    step_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.skip_step(current_user["user_id"], run_id, step_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("步骤已跳过", {"run": run})


@router.post("/api/runs/{run_id}/steps/{step_id}/complete", summary="完成步骤", response_model=APIResponse)
async def complete_step(
    run_id: str,
    step_id: str,
    request: StepCompleteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.complete_step(
            current_user["user_id"],
            run_id,
            step_id,
            output_data=request.output_data,
            artifacts=[item.model_dump() for item in request.artifacts],
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("步骤已完成", {"run": run})


@router.post(
    "/api/runs/{run_id}/steps/{step_id}/review",
    summary="Submit evidence for system-assisted review",
    response_model=APIResponse,
)
async def review_assisted_step(
    run_id: str,
    step_id: str,
    request: AssistedStepReviewRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.review_assisted_step(
            current_user["user_id"], run_id, step_id, request.model_dump()
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Review result updated", {"run": run})


@router.post("/api/runs/{run_id}/steps/{step_id}/fail", summary="记录步骤失败", response_model=APIResponse)
async def fail_step(
    run_id: str,
    step_id: str,
    request: StepFailRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.fail_step(
            current_user["user_id"], run_id, step_id, request.error_summary
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("步骤失败已记录", {"run": run})


@router.post("/api/runs/{run_id}/steps/{step_id}/retry", summary="重试步骤", response_model=APIResponse)
async def retry_step(
    run_id: str,
    step_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.retry_step(current_user["user_id"], run_id, step_id)
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("步骤已准备重试", {"run": run})


@router.post("/api/runs/{run_id}/steps/{step_id}/approvals", summary="请求确认", response_model=APIResponse)
async def request_approval(
    run_id: str,
    step_id: str,
    request: ApprovalRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        result = execution.request_approval(
            current_user["user_id"], run_id, step_id, request.model_dump()
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("已等待用户确认", result)


@router.post("/api/approvals/{approval_id}/resolve", summary="处理确认请求", response_model=APIResponse)
async def resolve_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.resolve_approval(
            current_user["user_id"], approval_id, request.decision, request.note
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    message = "已同意继续" if request.decision == "approved" else "已拒绝并停止执行"
    return create_success_response(message, {"run": run})


@router.post("/api/runs/{run_id}/steps/{step_id}/actions", summary="记录执行动作", response_model=APIResponse)
async def start_action(
    run_id: str,
    step_id: str,
    request: ActionStartRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        action = execution.start_action(
            current_user["user_id"], run_id, step_id, request.model_dump()
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行动作已记录", {"action": action})


@router.post(
    "/api/runs/{run_id}/steps/{step_id}/actions/{action_id}/complete",
    summary="完成执行动作",
    response_model=APIResponse,
)
async def complete_action(
    run_id: str,
    step_id: str,
    action_id: str,
    request: ActionCompleteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    execution: TaskExecution = Depends(get_task_execution),
) -> APIResponse:
    try:
        run = execution.complete_action(
            current_user["user_id"],
            run_id,
            step_id,
            action_id,
            status=request.status,
            output_data=request.output_data,
            error_summary=request.error_summary,
        )
    except TaskExecutionError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("执行动作已完成", {"run": run})
