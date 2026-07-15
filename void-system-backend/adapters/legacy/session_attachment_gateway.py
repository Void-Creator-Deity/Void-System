"""Legacy adapter for the existing session file manager."""
from __future__ import annotations

from typing import Any, Dict

from api.session_context_manager import SessionContextManager
from api.session_file_access import session_file_row_to_data_url
from core.session_attachment_contracts import SessionAttachmentGateway
from database import Database


class LegacySessionAttachmentGateway(SessionAttachmentGateway):
    """Keep the legacy filesystem manager behind a narrow attachment interface."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._manager = SessionContextManager(database.db_path)

    def owns_session(self, user_id: str, session_id: str) -> bool:
        return self._database.user_owns_chat_session(session_id, user_id)

    def create_session(self, user_id: str) -> Dict[str, Any]:
        return self._manager.create_new_session(user_id)

    def upload(self, user_id: str, session_id: str, file_data: bytes, file_name: str) -> Dict[str, Any]:
        return self._manager.upload_temporary_file(user_id, session_id, file_data, file_name)

    def context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        return self._manager.get_session_context(user_id, session_id)

    def active_sessions(self, user_id: str) -> Dict[str, Any]:
        return self._manager.get_active_sessions(user_id)

    def file_content(self, user_id: str, file_id: str) -> Dict[str, Any]:
        return self._manager.get_file_content(user_id, file_id)

    def delete_file(self, user_id: str, file_id: str) -> Dict[str, Any]:
        return self._manager.delete_session_file(user_id, file_id)

    def image_data_url(self, user_id: str, session_id: str, file_id: str) -> str | None:
        row = self._database.get_user_session_file(user_id, file_id)
        if row is None or row.get("session_id") != session_id:
            return None
        return session_file_row_to_data_url(row)
