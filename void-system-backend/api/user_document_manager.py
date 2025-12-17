"""
Void System - User Document Manager
-----------------------------------
用户文档管理器，实现DeepSeek风格的文件上传和处理
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio
import logging
from datetime import datetime

import sys
import os
# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import Database
from .user_document_parser import document_parser

logger = logging.getLogger("void-system-doc-manager")

class UserDocumentManager:
    """用户文档管理器"""

    def __init__(self, db_path: str = "void_system.db", storage_path: str = "./user_documents"):
        """
        初始化文档管理器
        Args:
            db_path: 数据库路径
            storage_path: 文件存储根目录
        """
        self.db = Database(db_path)
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 文件大小限制
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.preview_length = 500  # 预览文本长度

    async def upload_and_process_document(
        self,
        user_id: str,
        file_data: bytes,
        file_name: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        上传并处理文档（DeepSeek风格）
        Args:
            user_id: 用户ID
            file_data: 文件数据
            file_name: 原始文件名
            title: 文档标题（可选）
            tags: 标签列表（可选）
        Returns:
            处理结果
        """
        try:
            # 1. 文件验证
            validation = self._validate_file(file_data, file_name)
            if not validation["valid"]:
                return {
                    "success": False,
                    "message": validation["message"],
                    "error_code": "FILE_VALIDATION_FAILED"
                }

            # 2. 解析文件元数据
            metadata = document_parser.extract_metadata(file_data, file_name)

            # 3. 保存文件到存储
            doc_id = self._save_document_file(user_id, file_data, file_name)

            # 4. 创建数据库记录
            doc_title = title or self._generate_title(file_name, metadata)
            storage_path = self._get_storage_path(user_id, doc_id, file_name)

            doc_id = self.db.add_user_document(
                user_id=user_id,
                title=doc_title,
                original_name=file_name,
                file_type=metadata.get("file_type", "unknown"),
                file_size=len(file_data),
                storage_path=str(storage_path),
                content_preview="",  # 暂时为空，后续异步处理
                tags=tags or []
            )

            # 5. 异步处理文档内容
            asyncio.create_task(self._process_document_async(user_id, doc_id, file_data, file_name))

            return {
                "success": True,
                "message": "文档上传成功，正在处理中...",
                "doc_id": doc_id,
                "status": "processing"
            }

        except Exception as e:
            logger.error(f"文档上传失败: {str(e)}")
            return {
                "success": False,
                "message": f"文档上传失败: {str(e)}",
                "error_code": "UPLOAD_FAILED"
            }

    def get_user_documents(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取用户文档列表
        Args:
            user_id: 用户ID
            status: 状态筛选
            limit: 数量限制
            offset: 偏移量
        Returns:
            文档列表和统计信息
        """
        try:
            documents = self.db.get_user_documents(user_id, status, limit, offset)
            stats = self.db.get_user_document_stats(user_id)

            return {
                "success": True,
                "documents": documents,
                "stats": stats,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": len(documents) == limit
                }
            }
        except Exception as e:
            logger.error(f"获取文档列表失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取文档列表失败: {str(e)}",
                "documents": [],
                "stats": {}
            }

    def get_document(self, user_id: str, doc_id: str) -> Dict[str, Any]:
        """
        获取单个文档详情
        Args:
            user_id: 用户ID
            doc_id: 文档ID
        Returns:
            文档详情
        """
        try:
            document = self.db.get_user_document(user_id, doc_id)
            if not document:
                return {
                    "success": False,
                    "message": "文档不存在或无权访问",
                    "error_code": "DOCUMENT_NOT_FOUND"
                }

            return {
                "success": True,
                "document": document
            }
        except Exception as e:
            logger.error(f"获取文档失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取文档失败: {str(e)}"
            }

    def update_document_info(
        self,
        user_id: str,
        doc_id: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        更新文档信息
        Args:
            user_id: 用户ID
            doc_id: 文档ID
            title: 新标题
            tags: 新标签
        Returns:
            更新结果
        """
        try:
            success = self.db.update_user_document_info(doc_id, user_id, title, tags)
            if not success:
                return {
                    "success": False,
                    "message": "文档不存在或无权访问",
                    "error_code": "DOCUMENT_NOT_FOUND"
                }

            return {
                "success": True,
                "message": "文档信息更新成功"
            }
        except Exception as e:
            logger.error(f"更新文档信息失败: {str(e)}")
            return {
                "success": False,
                "message": f"更新文档信息失败: {str(e)}"
            }

    def delete_document(self, user_id: str, doc_id: str) -> Dict[str, Any]:
        """
        删除文档
        Args:
            user_id: 用户ID
            doc_id: 文档ID
        Returns:
            删除结果
        """
        try:
            # 获取文档信息
            document = self.db.get_user_document(user_id, doc_id)
            if not document:
                return {
                    "success": False,
                    "message": "文档不存在或无权访问",
                    "error_code": "DOCUMENT_NOT_FOUND"
                }

            # 删除物理文件
            storage_path = Path(document["storage_path"])
            if storage_path.exists():
                storage_path.unlink()

            # 删除数据库记录
            success = self.db.delete_user_document(doc_id, user_id)

            if success:
                return {
                    "success": True,
                    "message": "文档删除成功"
                }
            else:
                return {
                    "success": False,
                    "message": "文档删除失败"
                }
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return {
                "success": False,
                "message": f"删除文档失败: {str(e)}"
            }

    def _validate_file(self, file_data: bytes, file_name: str) -> Dict[str, Any]:
        """
        验证文件
        Args:
            file_data: 文件数据
            file_name: 文件名
        Returns:
            验证结果
        """
        # 检查文件大小
        if len(file_data) > self.max_file_size:
            return {
                "valid": False,
                "message": f"文件大小超过限制，最大允许 {self.max_file_size / 1024 / 1024:.1f}MB"
            }

        # 检查文件类型
        supported_types = document_parser.get_supported_types()
        file_type = file_name.split('.')[-1].lower() if '.' in file_name else ''

        if file_type and file_type not in supported_types:
            return {
                "valid": False,
                "message": f"不支持的文件类型: {file_type}，支持的类型: {', '.join(supported_types)}"
            }

        # 检查文件内容
        if len(file_data) == 0:
            return {
                "valid": False,
                "message": "空文件不允许上传"
            }

        return {"valid": True}

    def _save_document_file(self, user_id: str, file_data: bytes, file_name: str) -> str:
        """
        保存文档文件到存储
        Args:
            user_id: 用户ID
            file_data: 文件数据
            file_name: 文件名
        Returns:
            文档ID
        """
        import uuid
        doc_id = str(uuid.uuid4())

        # 创建用户目录
        user_dir = self.storage_path / user_id
        user_dir.mkdir(exist_ok=True)

        # 保存文件
        file_path = user_dir / f"{doc_id}_{file_name}"
        with open(file_path, 'wb') as f:
            f.write(file_data)

        return doc_id

    def _get_storage_path(self, user_id: str, doc_id: str, file_name: str) -> Path:
        """
        获取存储路径
        Args:
            user_id: 用户ID
            doc_id: 文档ID
            file_name: 文件名
        Returns:
            存储路径
        """
        return self.storage_path / user_id / f"{doc_id}_{file_name}"

    def _generate_title(self, file_name: str, metadata: Dict[str, Any]) -> str:
        """
        生成文档标题
        Args:
            file_name: 文件名
            metadata: 元数据
        Returns:
            标题
        """
        # 移除扩展名
        name_without_ext = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name

        # 标题化
        return name_without_ext.replace('_', ' ').replace('-', ' ').title()

    async def _process_document_async(self, user_id: str, doc_id: str, file_data: bytes, file_name: str):
        """
        异步处理文档内容
        Args:
            user_id: 用户ID
            doc_id: 文档ID
            file_data: 文件数据
            file_name: 文件名
        """
        try:
            # 1. 解析文档内容
            parse_result = document_parser.parse_file(file_data, file_name)

            if not parse_result.get("success", False):
                # 解析失败，更新状态
                self.db.update_user_document_status(
                    doc_id,
                    "failed",
                    error_message=parse_result.get("error", "解析失败")
                )
                return

            content = parse_result.get("content", "")
            content_preview = content[:self.preview_length] + "..." if len(content) > self.preview_length else content

            # 2. 更新预览内容
            # 这里需要添加一个数据库方法来更新预览内容
            # 暂时使用状态更新
            self.db.update_user_document_status(doc_id, "parsed")

            # 3. 创建向量嵌入（后续实现）
            # 这里会调用向量管理器来处理向量化

            logger.info(f"文档 {doc_id} 处理完成")

        except Exception as e:
            logger.error(f"文档异步处理失败 {doc_id}: {str(e)}")
            self.db.update_user_document_status(
                doc_id,
                "failed",
                error_message=f"处理失败: {str(e)}"
            )

# 全局文档管理器实例
document_manager = UserDocumentManager()
