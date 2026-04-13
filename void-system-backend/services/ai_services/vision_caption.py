"""
无会话历史的单次看图摘要（Composer 自动分析）。
"""
from __future__ import annotations

import logging
from typing import Union

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage

from services.ai_services.llm_factory import get_chat_llm
from services.ai_services.vision_messages import human_message_with_text_and_images

logger = logging.getLogger("void-system-vision")

CAPTION_SYSTEM = (
    "你是图像理解助理。用 2～5 句简体中文概括图片中的主体、场景、文字（若有）。"
    "不要标题或 Markdown，不要开场白，直接输出要点。"
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


async def caption_one_image_data_url(data_url: str) -> str:
    llm = get_chat_llm(temperature=0.2)
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
