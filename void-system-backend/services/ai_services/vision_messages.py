"""
多模态 HumanMessage 组装：persona 流与看图摘要共用。
"""
from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.messages import HumanMessage


def normalize_data_url(img: str) -> str:
    s = (img or "").strip()
    if s.startswith("data:"):
        return s
    return f"data:image/jpeg;base64,{s}"


def human_message_with_text_and_images(user_text: str, image_data_urls: List[str]) -> HumanMessage:
    blocks: List[Dict[str, Any]] = [{"type": "text", "text": user_text or " "}]
    for raw in image_data_urls:
        url = normalize_data_url(str(raw))
        blocks.append({"type": "image_url", "image_url": {"url": url}})
    return HumanMessage(content=blocks)
