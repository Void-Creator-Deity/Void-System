"""
Void System - RAG Document Manager
-----------------------------------
系统RAG文档管理器，用于处理管理员对系统知识库的增删改查操作。
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid
from datetime import datetime
import json
import sys
import os
# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import Database
from api.user_document_parser import document_parser
from config import config
from services.ai_services.llm_factory import get_embeddings

class SystemRAGManager:
    """
    系统RAG文档管理器 - 仅管理员操作
    负责系统知识库的文档管理，包括添加、删除、列出和更新文档。
    """

    def __init__(self, chroma_dir: Optional[str] = None, db_path: str = "void_system.db"):
        """
        初始化RAG文档管理器
        """
        self.chroma_dir = config.get_chroma_path() if chroma_dir is None else Path(chroma_dir).resolve()
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        # 与 qa_chain、用户向量共用同一嵌入工厂，保证入库与检索维度、模型一致
        self.embeddings = get_embeddings()

        # 初始化向量数据库
        self.vector_db = Chroma(
            persist_directory=str(self.chroma_dir),
            embedding_function=self.embeddings,
        )

        # 初始化数据库连接
        self.db = Database(db_path)

        # 智能切片器集合
        self.default_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, chunk_overlap=150,
            separators=["\ndef ", "\nclass ", "\n\n", "\n", " ", ""]
        )
        self.md_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, chunk_overlap=200,
            separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", " ", ""]
        )

    def _get_splitter(self, file_type: str):
        if file_type in {'py', 'js', 'java', 'cpp', 'ts'}: return self.code_splitter
        if file_type == 'md': return self.md_splitter
        return self.default_splitter

    def add_document_async(self, file_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步添加文档到系统知识库
        1. 立即返回成功状态
        2. 在后台进行解析和向量化
        """
        try:
            doc_id = str(uuid.uuid4())
            file_name = metadata.get("file_name", f"doc_{doc_id}.txt")
            file_type = file_name.split('.')[-1].lower() if '.' in file_name else "txt"
            
            # 记录元数据到数据库 (状态为 processing)
            self.db.add_system_rag_document(
                doc_id=doc_id,
                title=metadata["title"],
                uploaded_by=metadata["uploaded_by"],
                file_name=file_name,
                file_type=file_type,
                file_size=len(file_data),
                chroma_ids="[]",
                tags=metadata.get("tags", []),
                description=metadata.get("description", ""),
                is_active=True,
                parse_status="processing"
            )

            # 启动异步后台任务
            import asyncio
            asyncio.create_task(self._background_process(doc_id, file_data, file_name, metadata))

            return {
                "success": True,
                "doc_id": doc_id,
                "message": "文档已进入系统缓冲池，正在进行深度解析与向量化..."
            }
        except Exception as e:
            return {"success": False, "message": f"由系统注入失败: {str(e)}"}

    async def _background_process(self, doc_id: str, file_data: bytes, file_name: str, metadata: Dict[str, Any]):
        """后台处理线程：解析 + 切片 + 向量化"""
        try:
            # 1. 解析
            parse_result = document_parser.parse_file(file_data, file_name)
            if not parse_result.get("success"):
                self.db.update_system_rag_document_status(
                    doc_id, 
                    parse_status="failed",
                    error_message=parse_result.get("error", "解析失败")
                )
                return

            content = parse_result.get("content", "")
            file_type = file_name.split('.')[-1].lower() if '.' in file_name else "txt"

            # 2. 切片
            splitter = self._get_splitter(file_type)
            doc_chunks = splitter.create_documents([content])

            # 3. 增强元数据
            for i, chunk in enumerate(doc_chunks):
                chunk.metadata.update({
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "chunk_index": i,
                    "total_chunks": len(doc_chunks),
                    "upload_time": datetime.now().isoformat()
                })

            # 4. 向量化
            chroma_result = self.vector_db.add_documents(doc_chunks)

            # 5. 更新数据库
            self.db.update_system_rag_document(
                doc_id=doc_id,
                chroma_ids=json.dumps(chroma_result),
                parse_status="completed"
            )
            
        except Exception as e:
            print(f"RAG Background Error: {e}")
            self.db.update_system_rag_document_status(
                doc_id, 
                parse_status="failed",
                error_message=str(e)
            )

    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """
        从系统知识库删除文档
        Args:
            doc_id: 文档ID
        Returns:
            包含删除结果的字典
        """
        try:
            # 获取文档信息
            doc = self.db.get_system_rag_document(doc_id)
            if not doc:
                return {
                    "success": False,
                    "message": "文档不存在"
                }

            # 从Chroma中删除向量
            if doc.get("chroma_ids"):
                chroma_ids = json.loads(doc["chroma_ids"])
                if chroma_ids:
                    self.vector_db.delete(ids=chroma_ids)

            # 从SQLite中软删除文档
            result = self.db.delete_system_rag_document(doc_id)

            return {
                "success": result,
                "message": "文档删除成功" if result else "文档删除失败"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"文档删除失败: {str(e)}"
            }

    def list_documents(self, filter_tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        列出系统文档
        Args:
            filter_tags: 可选的标签过滤
        Returns:
            包含文档列表的字典
        """
        try:
            # 从SQLite获取文档列表
            docs = self.db.list_system_rag_documents(filter_tags)

            return {
                "success": True,
                "documents": docs,
                "count": len(docs)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取文档列表失败: {str(e)}"
            }

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """
        获取单个文档信息
        Args:
            doc_id: 文档ID
        Returns:
            包含文档信息的字典
        """
        try:
            doc = self.db.get_system_rag_document(doc_id)
            if not doc:
                return {
                    "success": False,
                    "message": "文档不存在"
                }

            return {
                "success": True,
                "document": doc
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取文档失败: {str(e)}"
            }

    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新文档元数据
        Args:
            doc_id: 文档ID
            updates: 要更新的字段，包括：
                - title: 文档标题
                - tags: 标签列表
                - description: 文档描述
                - is_active: 是否激活
        Returns:
            包含更新结果的字典
        """
        try:
            # 更新SQLite中的文档信息
            result = self.db.update_system_rag_document(
                doc_id=doc_id,
                title=updates.get("title"),
                tags=updates.get("tags"),
                description=updates.get("description"),
                is_active=updates.get("is_active")
            )

            return {
                "success": result,
                "message": "文档更新成功" if result else "文档更新失败"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"文档更新失败: {str(e)}"
            }

    def sync_chroma_with_db(self) -> Dict[str, Any]:
        """
        同步Chroma向量库与SQLite元数据
        Returns:
            包含同步结果的字典
        """
        try:
            # 获取活跃的系统文档
            active_docs = self.db.list_system_rag_documents()

            # 获取所有Chroma中的文档ID
            all_chroma_ids = self.vector_db.get()['ids']

            # 收集所有活跃文档的Chroma ID
            active_chroma_ids = []
            for doc in active_docs:
                if doc.get("chroma_ids"):
                    try:
                        chroma_ids = json.loads(doc["chroma_ids"])
                        active_chroma_ids.extend(chroma_ids)
                    except json.JSONDecodeError:
                        continue

            # 查找需要删除的Chroma ID（不在活跃文档中的ID）
            ids_to_delete = list(set(all_chroma_ids) - set(active_chroma_ids))

            # 删除无用的向量
            if ids_to_delete:
                self.vector_db.delete(ids=ids_to_delete)

            return {
                "success": True,
                "message": f"同步完成，删除了 {len(ids_to_delete)} 个无效向量",
                "deleted_ids_count": len(ids_to_delete)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"同步失败: {str(e)}"
            }
