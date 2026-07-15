"""
Void System - User Document Manager
-----------------------------------
用户文档管理器，实现虚空系统统一文件上传和处理流程
"""
from pathlib import Path
from typing import Awaitable, Callable, Dict, Any, Optional, List
import asyncio
import hashlib
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
ImageKnowledgeDescriber = Callable[[bytes, str], Awaitable[str]]


def _storage_safe_file_name(file_name: str) -> str:
    """Keep client-provided names from influencing the managed storage path."""
    raw_name = str(file_name or "").replace("\\", "/")
    candidate = raw_name.rsplit("/", 1)[-1].strip().replace("\x00", "")
    cleaned = "".join(
        "_" if ord(character) < 32 or character in '<>:\"/\\|?*' else character
        for character in candidate
    ).strip(". ")
    if not cleaned:
        cleaned = "upload"
    suffix = Path(cleaned).suffix[:20]
    stem = Path(cleaned).stem or "upload"
    max_stem_length = max(1, 180 - len(suffix))
    return f"{stem[:max_stem_length]}{suffix}"


class UserDocumentManager:
    """用户文档管理器"""

    def __init__(
        self,
        db_path: str = "void_system.db",
        storage_path: Optional[str] = None,
        database: Optional[Database] = None,
        vector_manager: Any = None,
        lifecycle_repository: Any = None,
        settings: Any = None,
        image_describer: Optional[ImageKnowledgeDescriber] = None,
    ):
        """Create a manager over application-supplied persistence resources."""
        self.db = database or Database(db_path)
        default_storage = Path(__file__).resolve().parents[1] / "user_documents"
        self.storage_path = Path(storage_path) if storage_path else default_storage
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._vector_manager = vector_manager
        self._lifecycle_repository = lifecycle_repository
        self._settings = settings
        self._image_describer = image_describer

        self.max_file_size = 50 * 1024 * 1024
        self.preview_length = 500

    def _get_vector_manager(self):
        if self._vector_manager is None:
            from .user_vector_manager import UserVectorManager

            self._vector_manager = UserVectorManager(database=self.db)
        return self._vector_manager

    async def upload_and_process_document(
        self,
        user_id: str,
        file_data: bytes,
        file_name: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        上传并处理文档（虚空系统标准流程）
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
                doc_id=doc_id,
                user_id=user_id,
                title=doc_title,
                original_name=file_name,
                file_type=metadata.get("file_type", "unknown"),
                file_size=len(file_data),
                storage_path=str(storage_path),
                content_preview="",  # 暂时为空，后续异步处理
                tags=tags or []
            )

            # Record a processing job before background work begins.
            lifecycle = self._start_ingestion_lifecycle(user_id, doc_id, file_data)

            # Continue processing without keeping the upload request open.
            asyncio.create_task(
                self._process_document_async(
                    user_id, doc_id, file_data, file_name, lifecycle.get("job_id")
                )
            )

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
            self._attach_lifecycle(documents, user_id)
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

            self._attach_lifecycle([document], user_id)
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
            # 1. 首先检查文档是否存在，使用轻量级的存在检查
            if not self.db.check_document_exists(doc_id, user_id):
                return {
                    "success": False,
                    "message": "文档不存在或无权访问",
                    "error_code": "DOCUMENT_NOT_FOUND"
                }
            
            # 2. 获取文档信息，用于后续操作
            document = self.db.get_user_document(user_id, doc_id)
            storage_path = None
            chroma_ids = []
            
            if document:
                # 记录存储路径用于删除物理文件
                storage_path = Path(document["storage_path"])
                # 记录chroma_ids用于删除向量索引
                chroma_ids = document.get("chroma_ids", [])
            
            # 3. Remove every indexed chunk before removing its source record.
            # If the index is unavailable, preserve the source so the user can retry
            # instead of leaving hidden, orphaned knowledge behind.
            if not self._get_vector_manager().delete_document_vectors(user_id, doc_id):
                return {
                    "success": False,
                    "message": "资料暂时无法从检索库移除，请稍后重试。",
                    "error_code": "VECTOR_DELETE_FAILED",
                }

            # 4. 执行数据库删除操作
            db_success = self.db.delete_user_document(doc_id, user_id)
            
            # 5. 删除物理文件（仅当数据库删除成功且文件存在时）
            file_deleted = False
            if db_success and storage_path and storage_path.exists():
                try:
                    storage_path.unlink()
                    file_deleted = True
                except Exception as e:
                    logger.error(f"删除物理文件失败: {str(e)}")
                    # 物理文件删除失败不影响整体删除结果
            
            # 6. 返回删除结果
            if db_success:
                return {
                    "success": True,
                    "message": "文档删除成功",
                    "data": {
                        "file_deleted": file_deleted
                    }
                }
            else:
                # 数据库删除失败，检查文档是否真的不存在
                if not self.db.check_document_exists(doc_id, user_id):
                    return {
                        "success": False,
                        "message": "文档不存在或无权访问",
                        "error_code": "DOCUMENT_NOT_FOUND"
                    }
                return {
                    "success": False,
                    "message": "数据库删除失败"
                }
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return {
                "success": False,
                "message": f"删除文档失败: {str(e)}"
            }

    async def rebuild_user_index(self, user_id: str) -> Dict[str, Any]:
        """Reparse stored source files and replace the user's vector index."""
        try:
            documents = self.db.get_user_documents(user_id, limit=500)
        except Exception as exc:
            logger.error("Could not list knowledge documents for index rebuild %s: %s", user_id, exc)
            return {
                "success": False,
                "message": "Unable to load documents for index rebuild",
                "error_code": "DOCUMENT_LIST_FAILED",
            }

        processed_documents = 0
        failed_documents = 0
        skipped_documents = 0
        total_vectors = 0
        failures = []

        for document in documents:
            doc_id = str(document.get("doc_id") or "")
            original_name = str(document.get("original_name") or "")
            raw_storage_path = document.get("storage_path")
            if not doc_id or not original_name or not raw_storage_path:
                skipped_documents += 1
                failures.append({"doc_id": doc_id or None, "reason": "Document metadata is incomplete"})
                continue

            storage_path = Path(str(raw_storage_path))
            if not storage_path.is_file():
                error_message = "Original file is missing and cannot be re-indexed"
                self.db.update_user_document_status(doc_id, "failed", error_message=error_message)
                failed_documents += 1
                failures.append({"doc_id": doc_id, "reason": error_message})
                continue

            try:
                file_data = storage_path.read_bytes()
                validation = self._validate_file(file_data, original_name)
                if not validation.get("valid"):
                    error_message = validation.get("message", "Source file validation failed")
                    self.db.update_user_document_status(doc_id, "failed", error_message=error_message)
                    failed_documents += 1
                    failures.append({"doc_id": doc_id, "reason": error_message})
                    continue

                if not self._get_vector_manager().delete_document_vectors(user_id, doc_id):
                    error_message = "Existing index could not be cleared; the original material was kept unchanged"
                    logger.error("Could not clear existing vectors before rebuilding %s", doc_id)
                    failed_documents += 1
                    failures.append({"doc_id": doc_id, "reason": error_message})
                    continue

                # Clear stale identifiers before parsing so failed rebuilds are never searchable.
                self.db.update_user_document_status(doc_id, "processing", chroma_ids=[])
                lifecycle = self._start_ingestion_lifecycle(user_id, doc_id, file_data)
                await self._process_document_async(
                    user_id, doc_id, file_data, original_name, lifecycle.get("job_id")
                )
                updated_document = self.db.get_user_document(user_id, doc_id) or {}
                if updated_document.get("parse_status") == "completed":
                    processed_documents += 1
                    total_vectors += len(updated_document.get("chroma_ids") or [])
                else:
                    failed_documents += 1
                    failures.append({
                        "doc_id": doc_id,
                        "reason": updated_document.get("error_message") or "Document indexing failed",
                    })
            except Exception as exc:
                error_message = f"Index rebuild failed: {str(exc)}"
                logger.exception("Knowledge index rebuild failed for %s", doc_id)
                self.db.update_user_document_status(doc_id, "failed", error_message=error_message)
                failed_documents += 1
                failures.append({"doc_id": doc_id, "reason": error_message})

        success = failed_documents == 0
        if success:
            message = f"Rebuilt {processed_documents} knowledge documents"
        else:
            message = f"Rebuilt {processed_documents} documents; {failed_documents} failed"
        return {
            "success": success,
            "message": message,
            "processed_documents": processed_documents,
            "failed_documents": failed_documents,
            "skipped_documents": skipped_documents,
            "total_vectors": total_vectors,
            "failures": failures,
        }

    async def _enrich_image_for_knowledge(
        self,
        file_data: bytes,
        file_name: str,
        parse_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Turn an image into grounded knowledge text through the configured vision path."""
        try:
            if self._image_describer is not None:
                content = await self._image_describer(file_data, file_name)
            else:
                from services.ai_services.vision_caption import describe_image_for_knowledge
                from services.ai_services.llm_factory import runtime_settings_scope

                if self._settings is None:
                    content = await describe_image_for_knowledge(file_data, file_name)
                else:
                    with runtime_settings_scope(self._settings):
                        content = await describe_image_for_knowledge(file_data, file_name)
        except Exception:
            logger.exception("Image knowledge extraction failed for %s", file_name)
            return {
                "success": False,
                "error": "图片资料暂时无法识别。请启用支持看图的 AI 服务，或改用可复制文本的文档。",
            }

        content = str(content or "").strip()
        if not content:
            return {
                "success": False,
                "error": "图片资料没有提取到可用于检索的内容。请上传更清晰的图片，或改用文本资料。",
            }
        enriched = dict(parse_result)
        enriched.update({
            "success": True,
            "content": content,
            "extraction_method": "vision",
        })
        enriched.pop("requires_vision_enrichment", None)
        return enriched

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
        safe_file_name = _storage_safe_file_name(file_name)
        file_path = user_dir / f"{doc_id}_{safe_file_name}"
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
        return self.storage_path / user_id / f"{doc_id}_{_storage_safe_file_name(file_name)}"

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

    def _start_ingestion_lifecycle(self, user_id: str, doc_id: str, file_data: bytes) -> Dict[str, Any]:
        if self._lifecycle_repository is None:
            return {}
        try:
            return self._lifecycle_repository.start_ingestion(
                document_id=doc_id,
                owner_id=user_id,
                content_fingerprint=hashlib.sha256(file_data).hexdigest(),
                source_size=len(file_data),
                index_version="legacy-chroma-v1",
            )
        except Exception as exc:
            logger.warning("Could not create knowledge ingestion record for %s: %s", doc_id, exc)
            return {}

    def _attach_lifecycle(self, documents: List[Dict[str, Any]], user_id: str) -> None:
        if self._lifecycle_repository is None:
            return
        for document in documents:
            try:
                document["knowledge_status"] = self._lifecycle_repository.latest_ingestion(
                    document_id=document["doc_id"], owner_id=user_id
                )
            except Exception:
                document["knowledge_status"] = None

    async def _process_document_async(
        self,
        user_id: str,
        doc_id: str,
        file_data: bytes,
        file_name: str,
        job_id: Optional[str] = None,
    ) -> None:
        """Parse, index, and record the outcome of one knowledge document."""
        try:
            if job_id and self._lifecycle_repository is not None:
                self._lifecycle_repository.update_ingestion(
                    job_id=job_id, owner_id=user_id, status="processing"
                )

            parse_result = document_parser.parse_file(file_data, file_name)
            if not parse_result.get("success", False):
                error_message = parse_result.get("error", "Document parsing failed")
                self.db.update_user_document_status(doc_id, "failed", error_message=error_message)
                if job_id and self._lifecycle_repository is not None:
                    self._lifecycle_repository.update_ingestion(
                        job_id=job_id,
                        owner_id=user_id,
                        status="failed",
                        error_message=error_message,
                    )
                return

            if parse_result.get("requires_vision_enrichment"):
                parse_result = await self._enrich_image_for_knowledge(file_data, file_name, parse_result)
                if not parse_result.get("success", False):
                    error_message = parse_result.get("error", "Image understanding failed")
                    self.db.update_user_document_status(doc_id, "failed", error_message=error_message)
                    if job_id and self._lifecycle_repository is not None:
                        self._lifecycle_repository.update_ingestion(
                            job_id=job_id,
                            owner_id=user_id,
                            status="failed",
                            error_message=error_message,
                        )
                    return

            content = parse_result.get("content", "")
            content_preview = content[:self.preview_length]
            if len(content) > self.preview_length:
                content_preview += "..."
            self.db.update_user_document_status(
                doc_id=doc_id,
                status="parsed",
                content_preview=content_preview,
            )

            vector_result = await self._get_vector_manager().process_and_store_document(
                user_id=user_id,
                doc_id=doc_id,
                content=content,
                metadata={
                    "file_name": file_name,
                    "title": self.db.get_user_document(user_id, doc_id).get("title", file_name),
                    "created_at": datetime.now().isoformat(),
                    "file_type": file_name.split(".")[-1].lower() if "." in file_name else "unknown",
                },
            )

            if not vector_result.get("success"):
                error_message = vector_result.get("message", "Document indexing failed")
                # Some adapters can write chunks but fail the final database update.
                # The document must still be visibly retryable rather than remaining "parsed".
                self.db.update_user_document_status(doc_id, "failed", error_message=error_message)
                if job_id and self._lifecycle_repository is not None:
                    self._lifecycle_repository.update_ingestion(
                        job_id=job_id,
                        owner_id=user_id,
                        status="failed",
                        error_message=error_message,
                    )
                return

            if job_id and self._lifecycle_repository is not None:
                self._lifecycle_repository.update_ingestion(
                    job_id=job_id,
                    owner_id=user_id,
                    status="completed",
                    chunk_count=int(vector_result.get("vector_count") or 0),
                    index_version="legacy-chroma-v1",
                )

            logger.info("Knowledge document %s processed", doc_id)
        except Exception as exc:
            logger.error("Knowledge document processing failed %s: %s", doc_id, exc)
            error_message = f"Document processing failed: {str(exc)}"
            self.db.update_user_document_status(doc_id, "failed", error_message=error_message)
            if job_id and self._lifecycle_repository is not None:
                self._lifecycle_repository.update_ingestion(
                    job_id=job_id,
                    owner_id=user_id,
                    status="failed",
                    error_message=error_message,
                )
