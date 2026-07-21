"""
无会话历史的单次看图摘要（Composer 自动分析）。
"""
from __future__ import annotations

import base64
import io
import logging
import mimetypes
from typing import Optional, Union

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage

from core.runtime_settings import RuntimeSettings
from services.ai_services.llm_factory import get_chat_llm
from services.ai_services.vision_messages import human_message_with_text_and_images

logger = logging.getLogger("void-system-vision")

CAPTION_SYSTEM = (
    "你是图像理解助理。用 2～5 句简体中文概括图片中的主体、场景、文字（若有）。"
    "不要标题或 Markdown，不要开场白，直接输出要点。"
)

KNOWLEDGE_IMAGE_SYSTEM = (
    "你是资料库的图片内容提取器。请先逐字转录清晰可见的文字、数字、表格字段和图表标签；"
    "再用简洁事实描述图片中的图表、流程、结构和关键结论。不要猜测看不清的内容，不要加入开场白。"
)


def _flatten_message_content(content: Union[str, list, None]) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts).strip()
    return str(content).strip()


async def caption_one_image_data_url(
    data_url: str, *, settings: Optional[RuntimeSettings] = None
) -> str:
    """Caption one session image using the caller's immutable AI settings.

    Inputs: a bounded image data URL and optional application settings snapshot.
    Output: a concise visible-text summary. Transport configuration stays in the
    canonical LLM factory, which prevents per-feature provider divergence.
    """
    llm = get_chat_llm(temperature=0.2, settings=settings)
    human = human_message_with_text_and_images("请根据附图输出概括。", [data_url])
    messages = [SystemMessage(content=CAPTION_SYSTEM), human]
    try:
        resp: BaseMessage = await llm.ainvoke(messages)
    except Exception:
        logger.exception("image caption ainvoke failed")
        raise
    text = _flatten_message_content(getattr(resp, "content", None))
    if isinstance(resp, AIMessage) and not text:
        text = _flatten_message_content(resp.content)
    return text or "（无法生成摘要）"


_MAX_VISION_PIXELS = 24_000_000
_MAX_VISION_EDGE = 2_048

def _image_data_url_for_vision(file_data: bytes, file_name: str) -> str:
    """Normalize an uploaded image into a bounded, widely-supported vision payload."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        mime_type = mimetypes.guess_type(file_name)[0] or "image/png"
        encoded = base64.b64encode(file_data).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    try:
        with Image.open(io.BytesIO(file_data)) as source:
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > _MAX_VISION_PIXELS:
                raise ValueError("Image dimensions exceed the knowledge extraction limit")
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((_MAX_VISION_EDGE, _MAX_VISION_EDGE))
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85, optimize=True)
    except (OSError, ValueError) as exc:
        raise ValueError("The uploaded image cannot be prepared for knowledge extraction") from exc

    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


async def describe_image_for_knowledge(
    file_data: bytes, file_name: str, *, settings: Optional[RuntimeSettings] = None
) -> str:
    """Produce searchable image evidence with a configured multimodal chat model.

    Inputs: file bytes, display name, and an optional application settings
    snapshot. Output: searchable factual image evidence. This is called by
    knowledge ingestion and must not read a mutable global model configuration.
    """
    data_url = _image_data_url_for_vision(file_data, file_name)
    llm = get_chat_llm(temperature=0.0, settings=settings)
    human = human_message_with_text_and_images(
        "请提取这张资料图片中可检索、可引用的事实内容。",
        [data_url],
    )
    response: BaseMessage = await llm.ainvoke([
        SystemMessage(content=KNOWLEDGE_IMAGE_SYSTEM),
        human,
    ])
    return _flatten_message_content(getattr(response, "content", None))
