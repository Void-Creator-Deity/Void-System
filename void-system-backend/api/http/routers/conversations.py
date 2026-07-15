"""HTTP Adapter for the Conversation module."""
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from api.http.dependencies import get_conversation_service, get_current_user
from api.http.responses import APIResponse, create_success_response
from api.http.schemas.conversations import (
    ChatGroupCreate,
    ChatGroupUpdate,
    ChatMessageCreate,
    ChatSessionCreate,
    ChatSessionUpdate,
)
from core.conversation_contracts import ConversationError
from errors import VoidSystemException
from modules.conversations.service import ConversationService


router = APIRouter(prefix="/api/chat", tags=["对话"])


def _translate_error(exc: ConversationError) -> VoidSystemException:
    return VoidSystemException(
        message=exc.message,
        error_code=exc.code,
        status_code=exc.status_code,
    )


@router.get("/groups", summary="获取对话分组及会话", response_model=APIResponse)
async def get_chat_history(
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    groups = conversations.list_groups(current_user["user_id"])
    return create_success_response("获取对话历史成功", data={"groups": groups})


@router.post("/groups", summary="创建对话分组", response_model=APIResponse)
async def create_chat_group(
    group_data: ChatGroupCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        group_id = conversations.create_group(
            current_user["user_id"], group_data.group_name
        )
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("分组创建成功", data={"group_id": group_id})


@router.put("/groups/{group_id}", summary="修改分组名称", response_model=APIResponse)
async def update_chat_group(
    group_id: str,
    group_data: ChatGroupUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        conversations.update_group(
            current_user["user_id"], group_id, group_data.group_name
        )
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("分组更新成功")


@router.delete("/groups/{group_id}", summary="删除对话分组", response_model=APIResponse)
async def delete_chat_group(
    group_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        conversations.delete_group(current_user["user_id"], group_id)
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("分组删除成功")


@router.post("/sessions", summary="创建对话会话", response_model=APIResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        session_id = conversations.create_session(
            current_user["user_id"],
            session_data.group_id,
            session_data.session_name,
            session_data.session_id,
        )
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("会话创建成功", data={"session_id": session_id})


@router.put("/sessions/{session_id}", summary="更新会话信息", response_model=APIResponse)
async def update_chat_session(
    session_id: str,
    session_data: ChatSessionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        conversations.update_session(
            current_user["user_id"],
            session_id,
            session_data.session_name,
            session_data.group_id,
        )
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("会话更新成功")


@router.delete("/sessions/{session_id}", summary="删除对话会话", response_model=APIResponse)
async def delete_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        conversations.delete_session(current_user["user_id"], session_id)
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("会话删除成功")


@router.post("/sessions/{session_id}/duplicate", summary="复制对话会话", response_model=APIResponse)
async def duplicate_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        new_id = conversations.duplicate_session(
            current_user["user_id"], session_id
        )
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("会话复制成功", data={"session_id": new_id})


@router.get("/sessions/{session_id}/messages", summary="获取历史消息", response_model=APIResponse)
async def get_chat_messages(
    session_id: str,
    limit: int = Query(100, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        messages = conversations.list_messages(
            current_user["user_id"], session_id, limit
        )
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("获取消息成功", data={"messages": messages})


@router.post("/sessions/{session_id}/messages", summary="新增对话消息", response_model=APIResponse)
async def add_chat_message(
    session_id: str,
    message_data: ChatMessageCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        message_id = conversations.add_message(
            current_user["user_id"],
            session_id,
            message_data.role,
            message_data.content,
            message_data.tokens,
            message_data.reply_to_id,
        )
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("消息添加成功", data={"message_id": message_id})


@router.delete("/sessions/{session_id}/messages", summary="清空对话历史", response_model=APIResponse)
async def clear_chat_messages(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    conversations: ConversationService = Depends(get_conversation_service),
) -> APIResponse:
    try:
        conversations.clear_messages(current_user["user_id"], session_id)
    except ConversationError as exc:
        raise _translate_error(exc) from exc
    return create_success_response("对话历史已清空")
