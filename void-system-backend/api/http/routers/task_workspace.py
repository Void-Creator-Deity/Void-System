"""Compatibility HTTP adapter for retired task and task-chain endpoints."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from api.http.dependencies import get_current_admin, get_current_user, get_task_workspace
from api.http.legacy_task_compatibility import legacy_task_metadata
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.task_workspace import TaskChainCreate, TaskCreate, TaskProgressUpdate
from core.task_workspace_contracts import TaskWorkspaceError
from errors import VoidSystemException
from modules.tasks.workspace import TaskWorkspace


logger = logging.getLogger("void-system.task-workspace")
router = APIRouter(tags=["tasks"])


def _translate_error(exc: TaskWorkspaceError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.post("/api/tasks", summary="Create legacy task", response_model=APIResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        task_id = workspace.create_task(current_user["user_id"], task_data.model_dump())
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(
        "Task created",
        {
            "task_id": task_id,
            "migration": legacy_task_metadata(
                workspace.execution_link(current_user["user_id"], task_id)
            ),
        },
    )


@router.get("/api/tasks", summary="List legacy tasks", response_model=APIResponse)
async def get_tasks(
    task_status: str | None = Query(None, alias="status"),
    category_id: str | None = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    data = workspace.list_tasks(
        current_user["user_id"],
        task_status=task_status,
        category_id=category_id,
        limit=limit,
        offset=offset,
    )
    data["migration"] = legacy_task_metadata()
    return create_success_response("Task list loaded", data)


@router.get("/api/tasks/{task_id}", summary="Get legacy task", response_model=APIResponse)
async def get_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        task = workspace.get_task(current_user["user_id"], task_id)
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(
        "Task loaded",
        {
            "task": task,
            "migration": legacy_task_metadata(
                workspace.execution_link(current_user["user_id"], task_id)
            ),
        },
    )


@router.delete("/api/tasks/{task_id}", summary="Delete legacy task", response_model=APIResponse)
async def delete_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    link = workspace.execution_link(current_user["user_id"], task_id)
    try:
        workspace.delete_task(current_user["user_id"], task_id)
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Task deleted", {"migration": legacy_task_metadata(link)})


@router.get("/api/task-chains", summary="List legacy task chains", response_model=APIResponse)
async def get_task_chains(
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    return create_success_response(
        "Task chains loaded",
        {"chains": workspace.list_chains(current_user["user_id"]), "migration": legacy_task_metadata()},
    )


@router.post("/api/task-chains", summary="Create legacy task chain", response_model=APIResponse)
async def create_task_chain(
    chain_data: TaskChainCreate,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    user_id = current_user["user_id"]
    try:
        creation = workspace.create_chain(user_id, chain_data.model_dump())
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc

    data = {
        "chain_id": creation.chain_id,
        "task_count": creation.task_count,
        "generation_status": creation.generation_status,
        "migration": legacy_task_metadata(
            workspace.chain_execution_link(user_id, creation.chain_id)
        ),
    }
    if chain_data.steps:
        return create_success_response("Task chain created", data)

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
                logger.warning("Task chain generation failed for %s: %s", creation.chain_id, exc.code)

        background_tasks.add_task(generate_tasks)
        return create_success_response("Task chain created; steps are being generated", data)

    return create_success_response("Task chain created", data)


@router.delete("/api/task-chains/{chain_id}", summary="Delete legacy task chain", response_model=APIResponse)
async def delete_task_chain(
    chain_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    link = workspace.chain_execution_link(current_user["user_id"], chain_id)
    try:
        workspace.delete_chain(current_user["user_id"], chain_id)
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Task chain deleted", {"migration": legacy_task_metadata(link)})


@router.put("/api/tasks/{task_id}/progress", summary="Update legacy task progress", response_model=APIResponse)
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
        "Task progress updated",
        {
            "progress": progress_data.progress,
            "reward_granted": reward_granted,
            "migration": legacy_task_metadata(
                workspace.execution_link(current_user["user_id"], task_id)
            ),
        },
    )


@router.get(
    "/api/admin/task-execution/legacy-audit",
    summary="Legacy task projection audit",
    response_model=APIResponse,
)
async def legacy_task_projection_audit(
    owner_id: str | None = Query(None),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    """Expose a read-only migration audit for operators during the compatibility window."""
    return create_success_response("Legacy task projection audit loaded", workspace.legacy_execution_audit(owner_id))
