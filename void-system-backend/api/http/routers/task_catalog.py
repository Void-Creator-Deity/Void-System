"""HTTP adapter for task category catalog operations."""
from typing import Any, Dict

from fastapi import APIRouter, Depends

from api.http.dependencies import get_current_user, get_task_workspace
from api.http.responses import APIResponse
from api.http.schemas.task_catalog import TaskCategoryCreate, TaskCategoryUpdate
from core.task_workspace_contracts import TaskWorkspaceError
from errors import VoidSystemException
from modules.tasks.workspace import TaskWorkspace


router = APIRouter(tags=["任务"])


def _translate_error(exc: TaskWorkspaceError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.get("/api/task-categories", summary="获取任务分类列表", response_model=APIResponse)
async def get_task_categories(
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    return APIResponse(
        success=True,
        message="任务分类列表获取成功",
        data={"categories": workspace.list_categories(current_user["user_id"])},
    )


@router.post("/api/task-categories", summary="创建任务分类", response_model=APIResponse)
async def create_task_category(
    category_data: TaskCategoryCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        category_id = workspace.create_category(
            current_user["user_id"], category_data.model_dump()
        )
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return APIResponse(success=True, message="任务分类创建成功", data={"category_id": category_id})


@router.put("/api/task-categories/{category_id}", summary="更新任务分类", response_model=APIResponse)
async def update_task_category(
    category_id: str,
    category_data: TaskCategoryUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        workspace.update_category(
            current_user["user_id"],
            category_id,
            category_data.model_dump(exclude_unset=True),
        )
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return APIResponse(success=True, message="任务分类更新成功")


@router.delete("/api/task-categories/{category_id}", summary="删除任务分类", response_model=APIResponse)
async def delete_task_category(
    category_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    workspace: TaskWorkspace = Depends(get_task_workspace),
) -> APIResponse:
    try:
        workspace.delete_category(current_user["user_id"], category_id)
    except TaskWorkspaceError as exc:
        raise _translate_error(exc) from exc
    return APIResponse(success=True, message="任务分类删除成功")
