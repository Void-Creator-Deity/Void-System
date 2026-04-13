"""
会话临时文件：读盘转 data URL（与路由鉴权解耦，仅做行级一致性检查）。
"""
from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from database import Database

logger = logging.getLogger("void-system-session")


def session_file_row_to_data_url(row: Dict[str, Any]) -> Optional[str]:
    """将已校验的 user_session_files 行转为 data URL。"""
    path_str = row.get("storage_path")
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_file():
        return None
    mime = row.get("mime_type") or mimetypes.guess_type(row.get("file_name") or "")[0] or "application/octet-stream"
    try:
        raw = p.read_bytes()
        b64 = base64.standard_b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except OSError as e:
        logger.warning("读取会话文件失败 %s: %s", path_str, e)
        return None


def load_session_image_data_url(
    db: Database, user_id: str, session_id: str, file_id: str
) -> Optional[str]:
    """读取用户在某会话下的临时文件为 data URL（须带 storage_path）。"""
    row = db.get_user_session_file(user_id, file_id)
    if not row or row.get("session_id") != session_id:
        return None
    return session_file_row_to_data_url(row)


def build_data_urls_for_session_files(
    db: Database, user_id: str, session_id: str, file_ids: List[str]
) -> List[str]:
    urls: List[str] = []
    for fid in file_ids:
        if not fid:
            continue
        u = load_session_image_data_url(db, user_id, session_id, fid)
        if u:
            urls.append(u)
    return urls
