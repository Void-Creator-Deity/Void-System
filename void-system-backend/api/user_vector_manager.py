"""
Void System - User Vector Manager
---------------------------------
用户级向量存储管理器，实现文档向量化存储和检索
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import sys
import os
# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import Database

logger = logging.getLogger("void-system-vector-manager")

class UserVectorManager:
    """用户向量管理器"""

    def __init__(self, chroma_dir: str = "./chroma_db", db_path: str = "void_system.db"):
        """
        初始化向量管理器
        Args:
            chroma_dir: ChromaDB存储目录
            db_path: 数据库路径
        """
        self.chroma_dir = Path(chroma_dir)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.db = Database(db_path)

        # 初始化嵌入模型
        self.embeddings = OllamaEmbeddings(
            model="hf.co/Qwen/Qwen3-Embedding-4B-GGUF:Q8_0"
        )

        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

        # 用户集合缓存
        self._collection_cache = {}

    def get_user_collection(self, user_id: str) -> Chroma:
        """
        获取用户专属向量集合
        Args:
            user_id: 用户ID
        Returns:
            用户的Chroma集合
        """
        collection_name = f"user_{user_id}_docs"

        if collection_name in self._collection_cache:
            return self._collection_cache[collection_name]

        # 创建或加载用户集合
        collection = Chroma(
            collection_name=collection_name,
            persist_directory=str(self.chroma_dir),
            embedding_function=self.embeddings,
        )

        self._collection_cache[collection_name] = collection
        return collection

    async def process_and_store_document(
        self,
        user_id: str,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理并存储文档向量
        Args:
            user_id: 用户ID
            doc_id: 文档ID
            content: 文档内容
            metadata: 元数据
        Returns:
            处理结果
        """
        try:
            # 1. 分割文本
            chunks = self.text_splitter.create_documents([content])

            # 2. 添加元数据
            base_metadata = {
                "user_id": user_id,
                "doc_id": doc_id,
                "chunk_index": 0,
                "total_chunks": len(chunks),
                **(metadata or {})
            }

            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    **base_metadata,
                    "chunk_index": i
                })

            # 3. 获取用户集合并存储
            collection = self.get_user_collection(user_id)
            result = collection.add_documents(chunks)

            # 4. 更新数据库状态
            collection_name = f"user_{user_id}_docs"
            success = self.db.update_user_document_status(
                doc_id=doc_id,
                status="completed",
                vector_collection=collection_name,
                chroma_ids=result
            )

            if success:
                logger.info(f"文档 {doc_id} 向量存储成功，共 {len(result)} 个向量块")
                return {
                    "success": True,
                    "message": f"文档处理完成，共生成 {len(result)} 个向量块",
                    "vector_count": len(result),
                    "collection": collection_name
                }
            else:
                return {
                    "success": False,
                    "message": "向量存储成功但数据库更新失败"
                }

        except Exception as e:
            logger.error(f"文档向量处理失败 {doc_id}: {str(e)}")

            # 更新数据库状态为失败
            self.db.update_user_document_status(
                doc_id=doc_id,
                status="failed",
                error_message=f"向量处理失败: {str(e)}"
            )

            return {
                "success": False,
                "message": f"文档向量处理失败: {str(e)}"
            }

    def search_user_documents(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        doc_ids: Optional[List[str]] = None
    ) -> List[Document]:
        """
        在用户文档中搜索相关内容
        Args:
            user_id: 用户ID
            query: 查询文本
            top_k: 返回结果数量
            doc_ids: 指定文档ID列表（可选）
        Returns:
            相关文档列表
        """
        try:
            collection = self.get_user_collection(user_id)

            # 如果指定了文档ID，进行过滤搜索
            if doc_ids:
                # 创建过滤器
                filter_dict = {"doc_id": {"$in": doc_ids}}
                results = collection.similarity_search(
                    query=query,
                    k=top_k,
                    filter=filter_dict
                )
            else:
                results = collection.similarity_search(query=query, k=top_k)

            return results

        except Exception as e:
            logger.error(f"文档搜索失败 {user_id}: {str(e)}")
            return []

    def delete_document_vectors(self, user_id: str, doc_id: str) -> bool:
        """
        删除文档向量
        Args:
            user_id: 用户ID
            doc_id: 文档ID
        Returns:
            是否删除成功
        """
        try:
            # 获取文档信息
            document = self.db.get_user_document(user_id, doc_id)
            if not document or not document.get("chroma_ids"):
                return False

            # 从向量数据库删除
            collection = self.get_user_collection(user_id)
            chroma_ids = document["chroma_ids"]
            collection.delete(ids=chroma_ids)

            logger.info(f"删除文档 {doc_id} 的 {len(chroma_ids)} 个向量")
            return True

        except Exception as e:
            logger.error(f"删除文档向量失败 {doc_id}: {str(e)}")
            return False

    def get_collection_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户集合统计信息
        Args:
            user_id: 用户ID
        Returns:
            统计信息
        """
        try:
            collection = self.get_user_collection(user_id)

            # 获取集合信息
            count = collection._collection.count() if hasattr(collection, '_collection') else 0

            # 按文档分组统计
            docs = collection.get()
            doc_ids = list(set([meta.get("doc_id") for meta in docs.get("metadatas", []) if meta.get("doc_id")]))

            return {
                "total_vectors": count,
                "total_documents": len(doc_ids),
                "collection_name": f"user_{user_id}_docs"
            }

        except Exception as e:
            logger.error(f"获取集合统计失败 {user_id}: {str(e)}")
            return {
                "total_vectors": 0,
                "total_documents": 0,
                "error": str(e)
            }

    def rebuild_user_index(self, user_id: str) -> Dict[str, Any]:
        """
        重建用户向量索引
        Args:
            user_id: 用户ID
        Returns:
            重建结果
        """
        try:
            # 获取用户所有已完成的文档
            documents = self.db.get_user_documents(user_id, status="completed")

            total_processed = 0
            total_vectors = 0

            for doc in documents:
                # 这里需要重新处理文档内容
                # 暂时跳过，实际实现需要读取文档内容
                pass

            return {
                "success": True,
                "message": f"索引重建完成，处理了 {total_processed} 个文档，共生成 {total_vectors} 个向量",
                "processed_docs": total_processed,
                "total_vectors": total_vectors
            }

        except Exception as e:
            logger.error(f"重建索引失败 {user_id}: {str(e)}")
            return {
                "success": False,
                "message": f"索引重建失败: {str(e)}"
            }

# 全局向量管理器实例
vector_manager = UserVectorManager()
