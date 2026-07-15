"""Temporary attachment session rules and stable result mapping."""
from __future__ import annotations

from typing import Any, Dict

from core.session_attachment_contracts import SessionAttachmentError, SessionAttachmentGateway


class SessionAttachments:
    def __init__(self, gateway: SessionAttachmentGateway) -> None:
        self._gateway = gateway

    def create_session(self, user_id: str) -> Dict[str, Any]:
        result = self._require_success(
            self._gateway.create_session(user_id),
            default_code="SESSION_CREATE_FAILED",
            default_message="Session could not be created",
        )
        return {"session_id": result.get("session_id"), "message": result.get("message", "Session created")}

    def upload(
        self, user_id: str, session_id: str, file_data: bytes, file_name: str
    ) -> Dict[str, Any]:
        self._require_session_owner(user_id, session_id)
        result = self._require_success(
            self._gateway.upload(user_id, session_id, file_data, file_name),
            default_code="SESSION_UPLOAD_FAILED",
            default_message="Attachment upload is temporarily unavailable",
        )
        return {
            "file_id": result["file_id"],
            "file_name": result.get("file_name"),
            "file_size": result.get("file_size"),
            "content_preview": result.get("content_preview"),
            "mime_type": result.get("mime_type"),
            "message": result.get("message", "Attachment uploaded"),
        }

    def context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        self._require_session_owner(user_id, session_id)
        result = self._require_success(
            self._gateway.context(user_id, session_id),
            default_code="SESSION_CONTEXT_FAILED",
            default_message="Session context is temporarily unavailable",
        )
        files = [self._public_file_row(dict(row)) for row in result.get("files", [])]
        return {"files": files, "file_count": len(files), "session_id": session_id}

    def active_sessions(self, user_id: str) -> Dict[str, Any]:
        result = self._require_success(
            self._gateway.active_sessions(user_id),
            default_code="SESSION_LIST_FAILED",
            default_message="Active sessions are temporarily unavailable",
        )
        return {
            "sessions": result.get("sessions", []),
            "session_count": result.get("session_count", 0),
            "message": result.get("message", "Active sessions loaded"),
        }

    def file_content(self, user_id: str, file_id: str) -> Dict[str, Any]:
        return self._require_success(
            self._gateway.file_content(user_id, file_id),
            default_code="SESSION_FILE_LOAD_FAILED",
            default_message="Attachment is temporarily unavailable",
        )

    def available_image_data_urls(self, user_id: str, session_id: str, file_ids: list[str]) -> list[str]:
        """Load only still-valid session images; chat remains usable when one expires."""
        return [
            data_url
            for file_id in file_ids
            if file_id
            for data_url in [self._gateway.image_data_url(user_id, session_id, file_id)]
            if data_url
        ]

    def image_data_url(self, user_id: str, session_id: str, file_id: str) -> str:
        self._require_session_owner(user_id, session_id)
        data_url = self._gateway.image_data_url(user_id, session_id, file_id)
        if not data_url:
            raise SessionAttachmentError(
                "Session image is unavailable", "SESSION_IMAGE_NOT_AVAILABLE", 400
            )
        return data_url

    def delete_file(self, user_id: str, file_id: str) -> str:
        result = self._require_success(
            self._gateway.delete_file(user_id, file_id),
            default_code="SESSION_FILE_DELETE_FAILED",
            default_message="Attachment could not be deleted",
        )
        return str(result.get("message", "Attachment deleted"))

    def _require_session_owner(self, user_id: str, session_id: str) -> None:
        if not self._gateway.owns_session(user_id, session_id):
            raise SessionAttachmentError("Session not found", "SESSION_NOT_FOUND", 404)

    @staticmethod
    def _public_file_row(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "file_id": row.get("id"),
            "file_name": row.get("file_name"),
            "file_size": row.get("original_size"),
            "upload_time": row.get("upload_time"),
            "content_preview": row.get("content_preview"),
            "mime_type": row.get("mime_type"),
        }

    @staticmethod
    def _require_success(
        result: Dict[str, Any], *, default_code: str, default_message: str
    ) -> Dict[str, Any]:
        if result.get("success"):
            return result
        status_code = int(result.get("status_code", 503))
        message = str(result.get("message") or default_message)
        if status_code >= 500:
            message = default_message
        raise SessionAttachmentError(
            message,
            str(result.get("error_code") or default_code),
            status_code,
        )
