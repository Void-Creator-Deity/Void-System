"""
Void System - Session Context Manager
-----------------------------------
会话级临时文件管理，用于处理用户在会话中上传的临时文件。
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
import uuid
import mimetypes
from datetime import datetime, timedelta
import sys
import os
import logging

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import Database

logger: logging.Logger = logging.getLogger("void-system-session")

# 常见图片扩展名（小写，不含点）
_IMAGE_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "webp", "gif", "bmp"})


class SessionContextManager:
    """
    会话级临时文件管理
    负责处理用户在会话中上传的临时文件，限制文件大小，提取文本内容，并设置过期时间。
    图片类文件会写入本地 storage_path，供多模态对话读取。
    """

    def __init__(self, db_path: str = "void_system.db", session_files_base: Optional[Path] = None):
        """
        Args:
            db_path: SQLite数据库文件路径
            session_files_base: 会话二进制文件根目录，默认使用 backend 下 data/session_temp
        """
        self.db = Database(db_path)
        self.max_file_size = 8 * 1024 * 1024  # 8MB
        self.max_content_preview_length = 500  # 内容预览最大长度
        if session_files_base is not None:
            self._session_files_base = Path(session_files_base)
        else:
            self._session_files_base = Path(backend_dir) / "data" / "session_temp"
        self._session_files_base.mkdir(parents=True, exist_ok=True)

    def _is_image_filename(self, file_name: str) -> bool:
        if "." not in file_name:
            return False
        ext = file_name.rsplit(".", 1)[-1].lower()
        return ext in _IMAGE_EXTENSIONS

    def upload_temporary_file(self, user_id: str, session_id: str, file_data: Any, file_name: str) -> Dict[str, Any]:
        """
        上传临时文件（不进入RAG）
        """
        try:
            validation = self.validate_file_upload(file_data, file_name)
            if not validation["success"]:
                return validation

            if len(file_data) > self.max_file_size:
                return {
                    "success": False,
                    "message": f"文件大小超过限制，最大允许 {self.max_file_size / 1024 / 1024:.1f}MB",
                }

            file_id = str(uuid.uuid4())
            storage_path: Optional[str] = None
            mime_type: Optional[str] = None

            if self._is_image_filename(file_name):
                ext = file_name.rsplit(".", 1)[-1].lower()
                user_dir = self._session_files_base / user_id
                user_dir.mkdir(parents=True, exist_ok=True)
                disk_path = user_dir / f"{file_id}.{ext}"
                disk_path.write_bytes(file_data)
                storage_path = str(disk_path.resolve())
                mime_type = mimetypes.guess_type(file_name)[0] or f"image/{ext}"
                content_preview = f"[图片文件] {file_name}"
            else:
                content_preview = ""
                try:
                    content = file_data.decode("utf-8")
                    content_preview = (
                        content[: self.max_content_preview_length] + "..."
                        if len(content) > self.max_content_preview_length
                        else content
                    )
                except UnicodeDecodeError:
                    try:
                        content = file_data.decode("gbk")
                        content_preview = (
                            content[: self.max_content_preview_length] + "..."
                            if len(content) > self.max_content_preview_length
                            else content
                        )
                    except UnicodeDecodeError:
                        content_preview = (
                            f"[无法预览的文件类型: {file_name.split('.')[-1] if '.' in file_name else 'unknown'}]"
                        )

            self.db.add_user_session_file(
                user_id=user_id,
                session_id=session_id,
                file_name=file_name,
                content_preview=content_preview,
                original_size=len(file_data),
                file_id=file_id,
                storage_path=storage_path,
                mime_type=mime_type,
            )

            return {
                "success": True,
                "file_id": file_id,
                "message": "临时文件上传成功",
                "file_name": file_name,
                "file_size": len(file_data),
                "content_preview": content_preview,
                "mime_type": mime_type,
            }
        except Exception as e:
            logger.error(f"上传临时文件失败: {str(e)}")
            return {
                "success": False,
                "message": f"文件上传失败: {str(e)}",
            }

    def get_session_context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        try:
            session_files = self.db.get_user_session_files(user_id, session_id)
            self.cleanup_expired_files()
            return {
                "success": True,
                "session_id": session_id,
                "files": session_files,
                "file_count": len(session_files),
            }
        except Exception as e:
            logger.error(f"获取会话上下文失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取会话上下文失败: {str(e)}",
            }

    def get_file_content(self, user_id: str, file_id: str) -> Dict[str, Any]:
        try:
            row = self.db.get_user_session_file(user_id, file_id)
            if not row:
                return {"success": False, "message": "文件不存在或已过期"}
            preview = row.get("content_preview") or ""
            return {
                "success": True,
                "message": "临时文件内容获取成功",
                "content_type": "preview_only",
                "content_preview": preview,
                "file_name": row.get("file_name"),
                "mime_type": row.get("mime_type"),
                "note": "二进制文件以磁盘路径存储，对话时通过多模态接口加载",
            }
        except Exception as e:
            logger.error(f"获取文件内容失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取文件内容失败: {str(e)}",
            }

    def delete_session_file(self, user_id: str, file_id: str) -> Dict[str, Any]:
        try:
            prev = self.db.delete_user_session_file(user_id, file_id)
            if not prev:
                return {"success": False, "message": "文件不存在或无权删除"}
            sp = prev.get("storage_path")
            if sp:
                try:
                    Path(sp).unlink(missing_ok=True)
                except OSError as oe:
                    logger.warning(f"删除磁盘临时文件失败 {sp}: {oe}")
            return {"success": True, "message": "临时文件删除成功"}
        except Exception as e:
            logger.error(f"删除临时文件失败: {str(e)}")
            return {
                "success": False,
                "message": f"删除临时文件失败: {str(e)}",
            }

    def cleanup_expired_files(self) -> Dict[str, Any]:
        try:
            paths = self.db.list_expired_session_file_storage_paths()
            for p in paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except OSError as oe:
                    logger.warning(f"清理过期文件磁盘失败 {p}: {oe}")
            deleted_count = self.db.cleanup_expired_session_files()
            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个过期的临时文件")
            return {
                "success": True,
                "message": f"清理了 {deleted_count} 个过期的临时文件",
                "deleted_count": deleted_count,
            }
        except Exception as e:
            logger.error(f"清理过期文件失败: {str(e)}")
            return {
                "success": False,
                "message": f"清理过期文件失败: {str(e)}",
            }

    def get_user_session_stats(self, user_id: str) -> Dict[str, Any]:
        try:
            return {
                "success": True,
                "message": "获取用户会话统计成功",
                "user_id": user_id,
                "stats": {
                    "active_sessions": 0,
                    "total_uploaded_files": 0,
                    "storage_used": 0,
                },
            }
        except Exception as e:
            logger.error(f"获取用户会话统计失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取用户会话统计失败: {str(e)}",
            }

    def validate_file_upload(self, file_data: bytes, file_name: str) -> Dict[str, Any]:
        if len(file_data) > self.max_file_size:
            return {
                "success": False,
                "message": f"文件大小超过限制，最大允许 {self.max_file_size / 1024 / 1024:.1f}MB",
            }

        allowed_extensions = {
            "txt",
            "md",
            "json",
            "csv",
            "pdf",
            "doc",
            "docx",
            "png",
            "jpg",
            "jpeg",
            "webp",
            "gif",
            "bmp",
        }
        file_extension = file_name.split(".")[-1].lower() if "." in file_name else ""

        if file_extension and file_extension not in allowed_extensions:
            return {
                "success": False,
                "message": f"不支持的文件类型: {file_extension}，允许的类型: {', '.join(sorted(allowed_extensions))}",
            }

        if len(file_data) == 0:
            return {
                "success": False,
                "message": "空文件不允许上传",
            }

        return {
            "success": True,
            "message": "文件验证通过",
        }

    def create_new_session(self, user_id: str) -> Dict[str, Any]:
        try:
            session_id = str(uuid.uuid4())
            return {
                "success": True,
                "session_id": session_id,
                "message": "新会话创建成功",
                "created_at": datetime.now().isoformat(),
                "expires_in": 86400,
            }
        except Exception as e:
            logger.error(f"创建新会话失败: {str(e)}")
            return {
                "success": False,
                "message": f"创建新会话失败: {str(e)}",
            }

    def get_active_sessions(self, user_id: str) -> Dict[str, Any]:
        try:
            return {
                "success": True,
                "message": "获取活跃会话成功",
                "sessions": [],
                "session_count": 0,
            }
        except Exception as e:
            logger.error(f"获取活跃会话失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取活跃会话失败: {str(e)}",
            }
