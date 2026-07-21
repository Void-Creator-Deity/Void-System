"""Administration HTTP adapter."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, Request, status
from starlette.concurrency import run_in_threadpool

from api.http.dependencies import get_current_admin
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.administration import (
    AIConfigModelListRequest,
    AIConfigTestRequest,
    AIConfigUpdateRequest,
)
from errors import VoidSystemException
from modules.administration.ai_configuration import AIConfigurationError, AIConfigurationManager


router = APIRouter(prefix="/api/admin/system", tags=["系统配置"])


def get_ai_configuration(request: Request) -> AIConfigurationManager:
    manager = getattr(request.app.state, "ai_configuration", None)
    if manager is None:
        raise VoidSystemException(
            message="模型连接配置尚未就绪。",
            error_code="AI_CONFIGURATION_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return manager


def _translate_error(exc: AIConfigurationError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=status.HTTP_400_BAD_REQUEST,
    )


@router.get("/ai-config", summary="获取模型连接配置", response_model=APIResponse)
async def get_ai_runtime_config(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: AIConfigurationManager = Depends(get_ai_configuration),
) -> APIResponse:
    del current_admin
    data = await run_in_threadpool(manager.read_profile)
    return create_success_response("模型连接配置获取成功", data=data)


@router.put("/ai-config", summary="更新模型连接配置", response_model=APIResponse)
async def update_ai_runtime_config(
    payload: AIConfigUpdateRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: AIConfigurationManager = Depends(get_ai_configuration),
) -> APIResponse:
    del current_admin
    try:
        data = await run_in_threadpool(manager.update_profile, payload.model_dump(exclude_unset=True))
    except AIConfigurationError as exc:
        raise _translate_error(exc) from exc
    message = "没有需要保存的变更" if not data["updated_keys"] else "模型连接配置已保存"
    return create_success_response(message, data=data)


@router.post("/ai-config/models", summary="获取上游模型列表", response_model=APIResponse)
async def discover_ai_models(
    payload: AIConfigModelListRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: AIConfigurationManager = Depends(get_ai_configuration),
) -> APIResponse:
    del current_admin
    try:
        data = await run_in_threadpool(
            manager.discover_models,
            payload.model_dump(exclude_unset=True),
        )
    except AIConfigurationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("上游模型列表已更新", data=data)


@router.post("/ai-config/test", summary="测试模型连接", response_model=APIResponse)
async def test_ai_runtime_config(
    payload: AIConfigTestRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    manager: AIConfigurationManager = Depends(get_ai_configuration),
) -> APIResponse:
    del current_admin
    try:
        data = await run_in_threadpool(manager.test_profile, payload.model_dump(exclude_unset=True))
    except AIConfigurationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("连接测试通过", data=data)
