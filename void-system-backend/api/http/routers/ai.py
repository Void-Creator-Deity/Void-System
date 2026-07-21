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

from api.http.dependencies import (
    get_current_user,
    get_current_user_optional,
    get_personal_context,
    get_runtime_settings,
    get_user_knowledge_resources,
    get_session_attachments,
)
from api.http.responses import APIResponse, create_success_response
from core.knowledge_contracts import KnowledgeQuery, KnowledgeScope
from core.model_connection_profile import ModelConnectionError
from core.runtime_settings import RuntimeSettings
from errors import VoidSystemException
from core.session_attachment_contracts import SessionAttachmentError
from modules.knowledge.service import UserKnowledgeResources
from modules.personal_context.service import PersonalContext
from modules.session_attachments.service import SessionAttachments


logger = logging.getLogger(__name__)
router = APIRouter()


_CONFIGURATION_MESSAGES = {
    "AI_PROVIDER_NOT_SUPPORTED": "当前 AI 服务商不受支持，请在系统设置中重新选择。",
    "AI_MODEL_REQUIRED": "请先在系统设置中选择对话模型。",
    "AI_CREDENTIAL_REQUIRED": "当前 AI 服务缺少访问密钥，请由管理员补全配置。",
    "AI_ENDPOINT_REQUIRED": "当前 AI 服务缺少上游地址，请由管理员补全配置。",
    "AI_PROTOCOL_NOT_SUPPORTED": "当前 AI 服务协议不受支持，请检查系统配置。",
}


def _model_connection_message(error: ModelConnectionError) -> str:
    """Return a safe action-oriented message for a canonical AI config error."""
    return _CONFIGURATION_MESSAGES.get(
        error.code,
        "AI 服务配置无效，请由管理员检查模型、地址和凭据。",
    )


def _model_connection_http_error(error: ModelConnectionError) -> VoidSystemException:
    """Translate a model configuration error into the shared HTTP envelope."""
    return VoidSystemException(
        message=_model_connection_message(error),
        error_code=error.code,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _library_context_for_message(
    resources: UserKnowledgeResources,
    *,
    owner_id: str,
    message: str,
) -> str:
    """Return small, relevant private-library excerpts for one chat turn.

    Inputs: the authenticated owner, their unified library resources, and the
    current chat message. Output: provider-safe cited excerpts from the user's
    uploads and shared documents already added to their library. Called only by
    the persona route after the user enables the knowledge context permission;
    retrieval failures intentionally leave ordinary chat available.
    """
    question = " ".join(str(message or "").split())
    if not question or resources is None:
        return ""
    try:
        chunks = resources.engine.search(
            KnowledgeQuery(
                owner_id=owner_id,
                question=question,
                scopes=(KnowledgeScope.USER, KnowledgeScope.SYSTEM),
                top_k=3,
                mode="hybrid",
                filters={"include_global_shared": False},
            )
        )
    except Exception:
        logger.exception("Personal library retrieval failed for persona chat")
        return ""

    excerpts = []
    for chunk in list(chunks)[:3]:
        text = " ".join(str(getattr(chunk, "text", "") or "").split())
        if not text:
            continue
        title = str(
            getattr(chunk, "title", None)
            or getattr(chunk, "file_name", None)
            or getattr(chunk, "document_id", "资料")
        )
        excerpts.append(f"[knowledge:{title}] {text[:900]}")
    return "\n".join(excerpts)


class StreamTextDelta:
    """Normalize provider chunks into append-only text deltas for SSE clients."""

    def __init__(self) -> None:
        self._emitted = ""

    def consume(self, value: Any) -> str:
        if isinstance(value, str):
            content = value
        elif isinstance(value, dict):
            content = value.get("content", "")
        elif hasattr(value, "content"):
            content = value.content
        else:
            content = ""

        if not isinstance(content, str) or not content:
            return ""
        if content.startswith(self._emitted):
            delta = content[len(self._emitted):]
            self._emitted = content
            return delta
        if self._emitted.endswith(content):
            return ""

        self._emitted += content
        return content


class ImageCaptionRequest(BaseModel):
    file_id: str = Field(..., min_length=1, max_length=80)
    session_id: str = Field(..., min_length=1, max_length=80)


class StreamChatRequest(BaseModel):
    type: Literal["persona", "qa"] = "persona"
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
    companion: PersonalContext = Depends(get_personal_context),
    settings: RuntimeSettings = Depends(get_runtime_settings),
    resources: UserKnowledgeResources = Depends(get_user_knowledge_resources),
):
    """Emit a stable SSE event stream without binding callers to a chain type."""
    if payload.type == "qa":
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
        personal_context = ""
        companion_settings: Dict[str, Any] = {}
        if current_user:
            try:
                companion_settings = companion.get_settings(current_user["user_id"])
            except Exception:
                # Presentation preferences must not make authorized context unavailable.
                logger.exception("Failed to load companion settings for persona chat")
            try:
                context_snapshot = companion.build_ai_context(
                    current_user["user_id"],
                    current_user,
                    purpose="conversation_assist",
                )
                personal_context = companion.render_ai_context(context_snapshot)
                if context_snapshot.get("permissions", {}).get("knowledge", False):
                    library_context = _library_context_for_message(
                        resources,
                        owner_id=current_user["user_id"],
                        message=payload.text,
                    )
                    if library_context:
                        personal_context = "\n\n".join(
                            part for part in (personal_context, library_context) if part
                        )
            except Exception:
                # Personal context should enrich chat, never make a conversation unavailable.
                logger.exception("Failed to build personal context for persona chat")
        try:
            chain = load_persona_chain(settings=settings)
        except ModelConnectionError as exc:
            raise _model_connection_http_error(exc) from exc
        input_data = {
            "text": payload.text,
            "images": merged_images,
            "personal_context": personal_context,
            "companion_settings": companion_settings,
            "session_id": session_id,
            "config": {"configurable": {"session_id": session_id}},
        }

    async def event_generator():
        stream_text = StreamTextDelta()
        try:
            async for chunk in chain.astream(input_data):
                delta = stream_text.consume(chunk)
                if delta:
                    yield {
                        "event": "message",
                        "data": json.dumps({"delta": delta, "finished": False}, ensure_ascii=False),
                    }
            yield {
                "event": "done",
                "data": json.dumps({"finished": True}, ensure_ascii=False),
            }
        except asyncio.CancelledError:
            raise
        except ModelConnectionError as exc:
            logger.warning("AI stream rejected by configuration: %s", exc.code)
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "message": _model_connection_message(exc),
                        "error_code": exc.code,
                        "finished": True,
                    },
                    ensure_ascii=False,
                ),
            }
        except Exception:
            logger.exception("AI streaming failed")
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "message": "AI 上游服务暂时不可用，请稍后重试。",
                        "error_code": "AI_UPSTREAM_UNAVAILABLE",
                        "finished": True,
                    },
                    ensure_ascii=False,
                ),
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
        summary = await caption_one_image_data_url(data_url, settings=settings)
    except ModelConnectionError as exc:
        raise _model_connection_http_error(exc) from exc
    except Exception as exc:
        logger.exception("Image caption failed")
        raise VoidSystemException(
            message="图像摘要服务暂时不可用，请稍后重试。",
            error_code="AI_UPSTREAM_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return create_success_response("摘要已生成", data={"summary": summary})
