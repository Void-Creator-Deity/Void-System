"""Identity and account HTTP routes."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from api.http.dependencies import (
    get_current_user,
    get_growth_profile,
    get_runtime_settings,
    get_user_service,
)
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.identity import (
    LoginRequest,
    LogoutRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RefreshTokenRequest,
    UserRegister,
)
from core.runtime_settings import RuntimeSettings
from errors import VoidSystemException
from modules.growth.profile import GrowthProfile


router = APIRouter()


def _client_metadata(request: Request) -> tuple[Optional[str], Optional[str]]:
    client = request.client
    return request.headers.get("user-agent"), client.host if client else None


@router.post("/api/auth/login", summary="用户登录", tags=["认证"], response_model=APIResponse)
async def login_json(
    payload: LoginRequest,
    request: Request,
    user_service=Depends(get_user_service),
) -> APIResponse:
    user_agent, ip_address = _client_metadata(request)
    result = user_service.authenticate_user(
        payload.identifier,
        payload.password,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return create_success_response("登录成功", data=result)


@router.post(
    "/api/token",
    summary="用户登录（OAuth2 兼容）",
    tags=["认证"],
    response_model=APIResponse,
    deprecated=True,
)
async def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service=Depends(get_user_service),
) -> APIResponse:
    user_agent, ip_address = _client_metadata(request)
    result = user_service.authenticate_user(
        form_data.username,
        form_data.password,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return create_success_response("登录成功", data=result)


@router.post("/api/auth/refresh", summary="刷新会话", tags=["认证"], response_model=APIResponse)
@router.post("/api/refresh-token", summary="刷新访问令牌（兼容）", tags=["认证"], response_model=APIResponse, deprecated=True)
async def refresh_token(
    payload: RefreshTokenRequest,
    user_service=Depends(get_user_service),
) -> APIResponse:
    return create_success_response("会话已刷新", data=user_service.refresh_user_token(payload.refresh_token))


@router.post("/api/auth/register", summary="用户注册", tags=["认证"], response_model=APIResponse)
@router.post("/api/register", summary="用户注册（兼容）", tags=["认证"], response_model=APIResponse, deprecated=True)
async def register(
    user_data: UserRegister,
    user_service=Depends(get_user_service),
) -> APIResponse:
    user_info = user_service.register_user(
        email=str(user_data.email),
        password=user_data.password,
        username=user_data.username,
    )
    return create_success_response("用户注册成功", data=user_info)


@router.post("/api/create-test-user", summary="创建测试用户", tags=["测试"], response_model=APIResponse)
async def create_test_user(
    user_service=Depends(get_user_service),
    settings: RuntimeSettings = Depends(get_runtime_settings),
) -> APIResponse:
    if not (settings.is_development() and settings.ENABLE_TEST_USER_ENDPOINT):
        raise VoidSystemException(
            message="该接口未启用",
            error_code="TEST_ENDPOINT_DISABLED",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    user_info = user_service.register_user(
        email="test@void-system.local",
        password="test-password-2026",
        username="测试用户",
    )
    return create_success_response("测试用户创建成功", data=user_info)


@router.post("/api/auth/logout", summary="用户登出", tags=["认证"], response_model=APIResponse)
@router.post("/api/logout", summary="用户登出（兼容）", tags=["用户"], response_model=APIResponse, deprecated=True)
async def logout(
    payload: Optional[LogoutRequest] = Body(default=None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_service=Depends(get_user_service),
) -> APIResponse:
    revocation_count = user_service.logout(
        current_user["user_id"],
        current_user["auth_session_id"],
        all_sessions=bool(payload and payload.all_sessions),
    )
    return create_success_response("登出成功", data={"revoked_sessions": revocation_count})


@router.get("/api/user/profile", summary="获取用户资料", tags=["用户"], response_model=APIResponse)
async def get_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    growth_profile: GrowthProfile = Depends(get_growth_profile),
    user_service=Depends(get_user_service),
) -> APIResponse:
    profile = user_service.get_user_profile(current_user["user_id"])
    profile.update(
        {
            "growth_points": growth_profile.balance(current_user["user_id"]),
            "stats": user_service.get_user_stats(current_user["user_id"]),
        }
    )
    return create_success_response("用户资料获取成功", data=profile)


@router.get("/api/user/stats", summary="获取用户统计信息", tags=["用户"], response_model=APIResponse)
async def get_user_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_service=Depends(get_user_service),
) -> APIResponse:
    stats = user_service.get_user_stats(current_user["user_id"])
    return create_success_response("用户统计信息获取成功", data=stats)


@router.put("/api/user/profile", summary="更新用户资料", tags=["用户"], response_model=APIResponse)
async def update_user_profile(
    payload: ProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_service=Depends(get_user_service),
) -> APIResponse:
    profile = user_service.update_user_profile(
        current_user["user_id"],
        payload.model_dump(exclude_none=True),
    )
    return create_success_response("用户资料更新成功", data=profile)


@router.put("/api/user/password", summary="修改密码", tags=["用户"], response_model=APIResponse)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_service=Depends(get_user_service),
) -> APIResponse:
    user_service.change_user_password(
        current_user["user_id"],
        payload.current_password,
        payload.new_password,
    )
    return create_success_response("密码已修改，请重新登录")
