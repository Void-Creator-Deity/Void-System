"""HTTP adapter for the user-facing Task Workspace."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from api.http.dependencies import get_current_user, get_task_workspace
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.task_workspace import TaskChainCreate, TaskCreate, TaskProgressUpdate
from core.task_workspace_contracts import TaskWorkspaceError
from errors import VoidSystemException
from modules.tasks.workspace import TaskWorkspace


logger = logging.getLogger("void-system.task-workspace")
router = APIRouter(tags=["任务"])


def _translate_error(exc: TaskWorkspaceError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.post("/api/tasks", summary="创建新任务", response_model=APIResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        task_id = workspace.create_task(current_user["user_id"], task_data.model_dump())
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return APIResponse(success=True, message="任务创建成功", data={"task_id": task_id})


@router.get("/api/tasks", summary="获取任务列表", response_model=APIResponse)
async def get_tasks(
    task_status: str | None = Query(None, alias="status"),
    category_id: str | None = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    return APIResponse(
        success=True,
        message="任务列表获取成功",
        data=workspace.list_tasks(
            current_user["user_id"],
            task_status=task_status,
            category_id=category_id,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/api/tasks/{task_id}", summary="获取任务详情", response_model=APIResponse)
async def get_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        task = workspace.get_task(current_user["user_id"], task_id)
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return APIResponse(success=True, message="任务详情获取成功", data={"task": task})


@router.delete("/api/tasks/{task_id}", summary="删除任务", response_model=APIResponse)
async def delete_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        workspace.delete_task(current_user["user_id"], task_id)
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return APIResponse(success=True, message="任务删除成功")


@router.get("/api/task-chains", summary="获取所有任务流程", response_model=APIResponse)
async def get_task_chains(
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    return create_success_response(
        "任务流程获取成功",
        {"chains": workspace.list_chains(current_user["user_id"])},
    )


@router.post("/api/task-chains", summary="创建任务流程", response_model=APIResponse)
async def create_task_chain(
    chain_data: TaskChainCreate,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    user_id = current_user["user_id"]
    values = chain_data.model_dump()
    try:
        creation = workspace.create_chain(user_id, values)
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc

    if chain_data.steps:
        return create_success_response(
            "任务流程及任务发布成功",
            {
                "chain_id": creation.chain_id,
                "task_count": creation.task_count,
                "generation_status": creation.generation_status,
            },
        )

    if chain_data.target_goal:
        def generate_tasks() -> None:
            try:
                workspace.generate_chain_steps(
                    user_id,
                    creation.chain_id,
                    chain_data.target_goal or "",
                    current_user,
                )
            except TaskWorkspaceError as exc:
                logger.warning(
                    "Task chain generation failed for %s: %s",
                    creation.chain_id,
                    exc.code,
                )

        background_tasks.add_task(generate_tasks)
        return create_success_response(
            "Task workflow created; steps are being generated",
            {"chain_id": creation.chain_id, "generation_status": creation.generation_status},
        )

    return create_success_response(
        "任务流程创建成功",
        {"chain_id": creation.chain_id, "generation_status": creation.generation_status},
    )


@router.delete("/api/task-chains/{chain_id}", summary="删除任务流程", response_model=APIResponse)
async def delete_task_chain(
    chain_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        workspace.delete_chain(current_user["user_id"], chain_id)
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("任务流程删除成功")


@router.put("/api/tasks/{task_id}/progress", summary="更新任务进度", response_model=APIResponse)
async def update_task_progress(
    task_id: str,
    progress_data: TaskProgressUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        reward_granted = workspace.update_task_progress(
            current_user["user_id"], task_id, progress_data.progress
        )
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(
        "进度更新成功",
        {"progress": progress_data.progress, "reward_granted": reward_granted},
    )
