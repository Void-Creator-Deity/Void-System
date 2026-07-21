"""HTTP adapter for Trigger-to-Run automation."""
from typing import Any, Dict

from fastapi import APIRouter, Depends

from api.http.dependencies import get_current_user, get_task_automation
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.task_automation import (
    TriggerCreate,
    TriggerFireRequest,
    TriggerUpdate,
)
from core.task_automation_contracts import TaskAutomationError
from errors import VoidSystemException
from modules.tasks.automation import TaskAutomation


router = APIRouter(tags=["Task Automation"])


def _translate_error(exc: TaskAutomationError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.post("/api/triggers", summary="Create trigger", response_model=APIResponse)
async def create_trigger(
    request: TriggerCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    automation: TaskAutomation = Depends(get_task_automation),
) -> APIResponse:
    try:
        trigger = automation.create_trigger(
            current_user["user_id"], request.model_dump()
        )
    except TaskAutomationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Trigger created", {"trigger": trigger})


@router.get("/api/triggers", summary="List triggers", response_model=APIResponse)
async def list_triggers(
    current_user: Dict[str, Any] = Depends(get_current_user),
    automation: TaskAutomation = Depends(get_task_automation),
) -> APIResponse:
    return create_success_response(
        "Triggers updated",
        {"triggers": automation.list_triggers(current_user["user_id"])},
    )


@router.get("/api/triggers/{trigger_id}", summary="Get trigger", response_model=APIResponse)
async def get_trigger(
    trigger_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    automation: TaskAutomation = Depends(get_task_automation),
) -> APIResponse:
    try:
        trigger = automation.get_trigger(current_user["user_id"], trigger_id)
    except TaskAutomationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Trigger updated", {"trigger": trigger})


@router.patch("/api/triggers/{trigger_id}", summary="Update trigger", response_model=APIResponse)
async def update_trigger(
    trigger_id: str,
    request: TriggerUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    automation: TaskAutomation = Depends(get_task_automation),
) -> APIResponse:
    try:
        trigger = automation.update_trigger(
            current_user["user_id"], trigger_id, request.model_dump(exclude_unset=True)
        )
    except TaskAutomationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Trigger updated", {"trigger": trigger})


@router.delete("/api/triggers/{trigger_id}", summary="Delete trigger", response_model=APIResponse)
async def delete_trigger(
    trigger_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    automation: TaskAutomation = Depends(get_task_automation),
) -> APIResponse:
    try:
        automation.delete_trigger(current_user["user_id"], trigger_id)
    except TaskAutomationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Trigger deleted")


@router.post("/api/triggers/{trigger_id}/pause", summary="Pause trigger", response_model=APIResponse)
async def pause_trigger(
    trigger_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    automation: TaskAutomation = Depends(get_task_automation),
) -> APIResponse:
    try:
        trigger = automation.pause_trigger(current_user["user_id"], trigger_id)
    except TaskAutomationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Trigger paused", {"trigger": trigger})


@router.post("/api/triggers/{trigger_id}/resume", summary="Resume trigger", response_model=APIResponse)
async def resume_trigger(
    trigger_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    automation: TaskAutomation = Depends(get_task_automation),
) -> APIResponse:
    try:
        trigger = automation.resume_trigger(current_user["user_id"], trigger_id)
    except TaskAutomationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Trigger resumed", {"trigger": trigger})


@router.post("/api/triggers/{trigger_id}/fire", summary="Fire trigger", response_model=APIResponse)
async def fire_trigger(
    trigger_id: str,
    request: TriggerFireRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    automation: TaskAutomation = Depends(get_task_automation),
) -> APIResponse:
    try:
        result = automation.fire_trigger(
            current_user["user_id"],
            trigger_id,
            request.source_key,
            request.payload,
        )
    except TaskAutomationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Trigger fired", result)
