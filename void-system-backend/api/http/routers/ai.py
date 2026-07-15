"""AI transport routes kept separate from application composition."""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from api.http.dependencies import get_current_user, get_current_user_optional, get_runtime_settings, get_session_attachments
from api.http.responses import APIResponse, create_success_response
from core.runtime_settings import RuntimeSettings
from core.session_attachment_contracts import SessionAttachmentError
from services.ai_services.llm_factory import runtime_settings_scope
from modules.session_attachments.service import SessionAttachments


logger = logging.getLogger(__name__)
router = APIRouter()


class ImageCaptionRequest(BaseModel):
    file_id: str = Field(..., min_length=1, max_length=80)
    session_id: str = Field(..., min_length=1, max_length=80)


class StreamChatRequest(BaseModel):
    type: Literal["persona", "advisor", "qa"] = "persona"
    topic: str = Field(default="", max_length=10_000)
    text: str = Field(default="", max_length=20_000)
    question: str = Field(default="", max_length=20_000)
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=80)
    images: list[str] = Field(default_factory=list, max_length=8)
    session_file_ids: list[str] = Field(default_factory=list, max_length=8)


@router.post("/api/stream-chat", tags=["AI服务"])
async def stream_chat_endpoint(
    payload: StreamChatRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
    attachments: SessionAttachments = Depends(get_session_attachments),
    settings: RuntimeSettings = Depends(get_runtime_settings),
):
    """Emit a stable SSE event stream without binding callers to a chain type."""
    if payload.type == "advisor":
        from services.ai_services.advisor_chain import load_task_chain

        with runtime_settings_scope(settings):
            chain = load_task_chain()
        input_data = {"topic": payload.topic}
    elif payload.type == "qa":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Legacy QA streaming has been retired; use /api/user/qa/ask instead",
        )
    else:
        from services.ai_services.persona_chain import load_persona_chain

        if payload.session_file_ids and not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="会话文件需要登录后使用")
        session_id = payload.session_id or f"anonymous-{secrets.token_urlsafe(12)}"
        merged_images = list(payload.images)
        if payload.session_file_ids and current_user:
            merged_images.extend(
                attachments.available_image_data_urls(
                    current_user["user_id"],
                    session_id,
                    payload.session_file_ids,
                )
            )
        with runtime_settings_scope(settings):
            chain = load_persona_chain()
        input_data = {
            "text": payload.text,
            "images": merged_images,
            "session_id": session_id,
            "config": {"configurable": {"session_id": session_id}},
        }

    async def event_generator():
        try:
            async for chunk in chain.astream(input_data):
                if hasattr(chunk, "content"):
                    content = chunk.content
                elif isinstance(chunk, str):
                    content = chunk
                elif isinstance(chunk, dict):
                    content = chunk.get("content", "")
                else:
                    content = ""
                if content:
                    yield {
                        "event": "message",
                        "data": json.dumps({"content": content, "finished": False}, ensure_ascii=False),
                    }
            yield {
                "event": "done",
                "data": json.dumps({"finished": True}, ensure_ascii=False),
            }
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI streaming failed")
            yield {
                "event": "error",
                "data": json.dumps({"message": "AI 服务暂时不可用", "finished": True}, ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


@router.post("/api/ai/image-caption", summary="会话图片无状态摘要", tags=["AI服务"], response_model=APIResponse)
async def image_caption_endpoint(
    body: ImageCaptionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    attachments: SessionAttachments = Depends(get_session_attachments),
    settings: RuntimeSettings = Depends(get_runtime_settings),
) -> APIResponse:
    from services.ai_services.vision_caption import caption_one_image_data_url

    try:
        data_url = attachments.image_data_url(current_user["user_id"], body.session_id, body.file_id)
    except SessionAttachmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    try:
        with runtime_settings_scope(settings):
            summary = await caption_one_image_data_url(data_url)
    except Exception as exc:
        logger.exception("Image caption failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="模型摘要暂时不可用") from exc
    return create_success_response("摘要已生成", data={"summary": summary})
