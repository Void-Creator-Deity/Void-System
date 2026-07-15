"""HTTP adapter for per-session temporary attachments."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Query, UploadFile

from api.http.dependencies import get_current_user, get_session_attachments
from api.http.responses import APIResponse, create_success_response
from core.session_attachment_contracts import SessionAttachmentError
from errors import VoidSystemException
from modules.session_attachments.service import SessionAttachments


router = APIRouter(tags=["Session Attachments"])


def _translate_error(exc: SessionAttachmentError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.post("/api/session/new", summary="Create a temporary session", response_model=APIResponse)
async def session_create_standalone(
    current_user: Dict[str, Any] = Depends(get_current_user),
    attachments: SessionAttachments = Depends(get_session_attachments),
) -> APIResponse:
    try:
        result = attachments.create_session(current_user["user_id"])
    except SessionAttachmentError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(result["message"], data={"session_id": result["session_id"]})


@router.post("/api/session/upload-temporary", summary="Upload a session attachment", response_model=APIResponse)
async def session_upload_temporary(
    session_id: str = Query(..., description="Current user's chat session id"),
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    attachments: SessionAttachments = Depends(get_session_attachments),
) -> APIResponse:
    try:
        result = attachments.upload(
            current_user["user_id"], session_id, await file.read(), file.filename or "unnamed"
        )
    except SessionAttachmentError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(
        result.pop("message"),
        data=result,
    )


@router.get("/api/session/context/{session_id}", summary="List session attachments", response_model=APIResponse)
async def session_get_context(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    attachments: SessionAttachments = Depends(get_session_attachments),
) -> APIResponse:
    try:
        result = attachments.context(current_user["user_id"], session_id)
    except SessionAttachmentError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("Session context loaded", data=result)


@router.get("/api/session/active", summary="List active temporary sessions", response_model=APIResponse)
async def session_get_active(
    current_user: Dict[str, Any] = Depends(get_current_user),
    attachments: SessionAttachments = Depends(get_session_attachments),
) -> APIResponse:
    try:
        result = attachments.active_sessions(current_user["user_id"])
    except SessionAttachmentError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(
        result.pop("message"),
        data=result,
    )


@router.get("/api/session/files/{file_id}", summary="Get a session attachment", response_model=APIResponse)
async def session_get_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    attachments: SessionAttachments = Depends(get_session_attachments),
) -> APIResponse:
    try:
        result = attachments.file_content(current_user["user_id"], file_id)
    except SessionAttachmentError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(result.get("message", "Attachment loaded"), data=result)


@router.delete("/api/session/files/{file_id}", summary="Delete a session attachment", response_model=APIResponse)
async def session_delete_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    attachments: SessionAttachments = Depends(get_session_attachments),
) -> APIResponse:
    try:
        message = attachments.delete_file(current_user["user_id"], file_id)
    except SessionAttachmentError as exc:
        raise _translate_error(exc) from exc
    return create_success_response(message)
