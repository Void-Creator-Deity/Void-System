"""Conversation workflow with ownership and lifecycle invariants."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from adapters.sqlite.conversation_repository import SQLiteConversationRepository
from core.conversation_contracts import ConversationError, ConversationRepository
from database import Database


class ConversationService:
    def __init__(self, repository: ConversationRepository):
        self._repository = repository

    @staticmethod
    def _required_name(value: str, label: str, maximum: int) -> str:
        value = value.strip()
        if not value:
            raise ConversationError("INVALID_NAME", f"{label}不能为空")
        if len(value) > maximum:
            raise ConversationError("INVALID_NAME", f"{label}不能超过 {maximum} 个字符")
        return value

    @staticmethod
    def _not_found(kind: str) -> ConversationError:
        return ConversationError(
            "CONVERSATION_NOT_FOUND",
            f"{kind}不存在或无权访问",
            404,
        )

    def list_groups(self, user_id: str) -> List[Dict[str, Any]]:
        return self._repository.list_groups(user_id)

    def create_group(self, user_id: str, name: str) -> str:
        return self._repository.create_group(
            user_id,
            self._required_name(name, "分组名称", 50),
        )

    def update_group(self, user_id: str, group_id: str, name: str) -> None:
        if not self._repository.update_group(
            user_id,
            group_id,
            self._required_name(name, "分组名称", 50),
        ):
            raise self._not_found("分组")

    def delete_group(self, user_id: str, group_id: str) -> None:
        if not self._repository.delete_group(user_id, group_id):
            raise self._not_found("分组")

    def create_session(
        self,
        user_id: str,
        group_id: str,
        name: str,
        session_id: Optional[str] = None,
    ) -> str:
        result = self._repository.create_session(
            user_id,
            group_id,
            self._required_name(name, "会话名称", 100),
            session_id,
        )
        if result is None:
            raise self._not_found("目标分组")
        return result

    def update_session(
        self,
        user_id: str,
        session_id: str,
        name: Optional[str],
        group_id: Optional[str],
    ) -> None:
        clean_name = None if name is None else self._required_name(name, "会话名称", 100)
        if clean_name is None and group_id is None:
            raise ConversationError("EMPTY_UPDATE", "请至少修改一项会话信息")
        if not self._repository.update_session(user_id, session_id, clean_name, group_id):
            raise self._not_found("会话或目标分组")

    def delete_session(self, user_id: str, session_id: str) -> None:
        if not self._repository.delete_session(user_id, session_id):
            raise self._not_found("会话")

    def duplicate_session(self, user_id: str, session_id: str) -> str:
        result = self._repository.duplicate_session(user_id, session_id)
        if result is None:
            raise self._not_found("会话")
        return result

    def list_messages(self, user_id: str, session_id: str, limit: int) -> List[Dict[str, Any]]:
        result = self._repository.list_messages(user_id, session_id, limit)
        if result is None:
            raise self._not_found("会话")
        return result

    def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        tokens: int = 0,
        reply_to_id: Optional[str] = None,
    ) -> str:
        content = content.strip()
        if not content:
            raise ConversationError("EMPTY_MESSAGE", "消息内容不能为空")
        if role not in {"user", "assistant", "system"}:
            raise ConversationError("INVALID_MESSAGE_ROLE", "消息角色无效")
        result = self._repository.add_message(
            user_id,
            session_id,
            role,
            content,
            max(0, tokens),
            reply_to_id,
        )
        if result is None:
            raise self._not_found("会话或引用消息")
        return result

    def clear_messages(self, user_id: str, session_id: str) -> None:
        if not self._repository.clear_messages(user_id, session_id):
            raise self._not_found("会话")


def get_conversation_service(database: Database) -> ConversationService:
    repository = SQLiteConversationRepository(database.get_connection)
    return ConversationService(repository)
