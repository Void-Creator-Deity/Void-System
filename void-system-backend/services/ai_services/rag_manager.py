"""
Void System - RAG Document Manager
-----------------------------------
系统RAG文档管理器，用于处理管理员对系统知识库的增删改查操作。
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
from langchain_ollama import OllamaEmbeddings
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

class SystemRAGManager:
    """
    系统RAG文档管理器 - 仅管理员操作
    负责系统知识库的文档管理，包括添加、删除、列出和更新文档。
    """

    def __init__(self, chroma_dir: str = "./chroma_db", db_path: str = "void_system.db"):
        """
        初始化RAG文档管理器
        Args:
            chroma_dir: ChromaDB持久化目录
            db_path: SQLite数据库文件路径
        """
        self.chroma_dir = Path(chroma_dir).resolve()
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        # 初始化嵌入模型
        self.embeddings = OllamaEmbeddings(
            model="hf.co/Qwen/Qwen3-Embedding-4B-GGUF:Q8_0"
        )

        # 初始化向量数据库
        self.vector_db = Chroma(
            persist_directory=str(self.chroma_dir),
            embedding_function=self.embeddings,
        )

        # 初始化数据库连接
        self.db = Database(db_path)

        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

    def add_document_to_system(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加文档到系统知识库
        Args:
            file_path: 文件路径
            metadata: 文档元数据，包括：
                - title: 文档标题
                - uploaded_by: 上传者ID
                - tags: 标签列表
                - description: 文档描述
        Returns:
            包含文档ID和相关信息的字典
        """
        try:
            # 读取文件内容
            file = Path(file_path)
            file_name = file.name
            file_type = file.suffix[1:].lower() if file.suffix else "txt"
            file_size = file.stat().st_size

            # 允许的文件类型（仅支持文本文件）
            allowed_file_types = {"txt", "md", "json", "csv", "py", "js", "html", "css", "xml"}
            if file_type not in allowed_file_types:
                return {
                    "success": False,
                    "message": f"不支持的文件类型: {file_type}。仅支持以下文本文件类型: {', '.join(allowed_file_types)}"
                }

            # 读取文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                return {
                    "success": False,
                    "message": "无法读取文件内容，仅支持UTF-8编码的文本文件"
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"读取文件失败: {str(e)}"
                }

            # 检查文件内容是否为空
            if not content.strip():
                return {
                    "success": False,
                    "message": "文件内容为空，无法添加到知识库"
                }

            # 分割文本为文档块
            doc_chunks = self.text_splitter.create_documents([content])

            # 添加元数据到每个块
            for i, chunk in enumerate(doc_chunks):
                chunk.metadata.update({
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_size": file_size,
                    "chunk_index": i,
                    "total_chunks": len(doc_chunks),
                    "uploaded_by": metadata["uploaded_by"],
                    "upload_time": datetime.now().isoformat()
                })

            # 生成向量并存储到Chroma
            chroma_result = self.vector_db.add_documents(doc_chunks)
            chroma_ids = json.dumps(chroma_result)

            # 记录元数据到SQLite
            doc_id = self.db.add_system_rag_document(
                title=metadata["title"],
                uploaded_by=metadata["uploaded_by"],
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                chroma_ids=chroma_ids,
                tags=metadata.get("tags", []),
                description=metadata.get("description", "")
            )

            return {
                "success": True,
                "doc_id": doc_id,
                "message": "文档添加成功",
                "chroma_ids_count": len(chroma_result)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"文档添加失败: {str(e)}"
            }

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
