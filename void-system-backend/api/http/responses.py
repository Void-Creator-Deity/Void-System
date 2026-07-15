"""Shared HTTP response contracts for the Growth App."""
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class APIResponse(BaseModel):
    """Stable response envelope used by the existing public API."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    error_code: Optional[str] = None
    details: Optional[Any] = None
    request_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "操作成功",
                "data": {"key": "value"},
                "error_code": None,
                "details": None,
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }
    )


def create_success_response(
    message: str,
    data: Optional[Any] = None,
    request_id: Optional[str] = None,
) -> APIResponse:
    return APIResponse(
        success=True,
        message=message,
        data=data,
        request_id=request_id,
    )


def create_error_response(
    message: str,
    error_code: Optional[str] = None,
    data: Optional[Any] = None,
    details: Optional[Any] = None,
    request_id: Optional[str] = None,
) -> APIResponse:
    return APIResponse(
        success=False,
        message=message,
        error_code=error_code,
        data=data,
        details=details,
        request_id=request_id,
    )
