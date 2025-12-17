"""
Void System - Personalized QA Engine
------------------------------------
个性化RAG问答引擎，基于用户文档进行智能问答
"""
from typing import Dict, Any, Optional, List
import logging
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from .user_vector_manager import vector_manager

logger = logging.getLogger("void-system-personalized-qa")

class PersonalizedQAEngine:
    """个性化问答引擎"""

    def __init__(self):
        # 初始化LLM
        self.llm = ChatOllama(
            model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M",
            temperature=0.3  # 较低温度保证回答稳定性
        )

        # 定义问答提示模板
        self.qa_prompt = ChatPromptTemplate.from_template("""
        你是虚空系统的智能助手，专门基于用户提供的文档内容回答问题。

        相关文档内容：
        ----------------
        {context}
        ----------------

        用户问题：{question}

        回答要求：
        1. **基于文档内容**：严格基于提供的文档内容回答，不要编造信息
        2. **准确引用**：尽可能引用文档中的具体内容和数据
        3. **逻辑清晰**：回答要有逻辑层次，重点突出
        4. **简洁明了**：不要冗长，抓住核心要点
        5. **客观中立**：保持客观，基于事实回答

        如果文档中没有相关信息，请明确说明"根据提供的文档内容，无法回答这个问题"。

        回答：
        """)

        # 创建问答链
        self.qa_chain = self.qa_prompt | self.llm | StrOutputParser()

    async def answer_question(
        self,
        user_id: str,
        question: str,
        selected_doc_ids: Optional[List[str]] = None,
        max_docs: int = 5
    ) -> Dict[str, Any]:
        """
        基于用户文档回答问题
        Args:
            user_id: 用户ID
            question: 问题文本
            selected_doc_ids: 指定文档ID列表（可选）
            max_docs: 最大检索文档数量
        Returns:
            回答结果
        """
        try:
            # 1. 检索相关文档
            relevant_docs = self._retrieve_relevant_documents(
                user_id, question, selected_doc_ids, max_docs
            )

            if not relevant_docs:
                return {
                    "success": True,
                    "answer": "抱歉，没有找到相关的文档内容来回答这个问题。请确保您已上传相关文档。",
                    "sources": [],
                    "confidence": 0
                }

            # 2. 构建上下文
            context = self._build_context(relevant_docs)

            # 3. 生成回答
            answer = await self.qa_chain.ainvoke({
                "context": context,
                "question": question
            })

            # 4. 提取来源信息
            sources = self._extract_sources(relevant_docs)

            # 5. 计算置信度（简单版本）
            confidence = self._calculate_confidence(relevant_docs, question)

            return {
                "success": True,
                "answer": answer.strip(),
                "sources": sources,
                "confidence": confidence,
                "retrieved_docs_count": len(relevant_docs)
            }

        except Exception as e:
            logger.error(f"问答失败 {user_id}: {str(e)}")
            return {
                "success": False,
                "answer": f"抱歉，处理您的问题时出现了错误：{str(e)}",
                "sources": [],
                "error": str(e)
            }

    def _retrieve_relevant_documents(
        self,
        user_id: str,
        question: str,
        selected_doc_ids: Optional[List[str]] = None,
        max_docs: int = 5
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        Args:
            user_id: 用户ID
            question: 问题
            selected_doc_ids: 指定文档ID
            max_docs: 最大文档数
        Returns:
            相关文档列表
        """
        try:
            # 使用向量管理器检索
            search_results = vector_manager.search_user_documents(
                user_id=user_id,
                query=question,
                top_k=max_docs * 2,  # 多检索一些，用于后续去重
                doc_ids=selected_doc_ids
            )

            # 转换为字典格式并去重
            seen_docs = set()
            relevant_docs = []

            for doc in search_results:
                doc_id = doc.metadata.get("doc_id")
                if doc_id and doc_id not in seen_docs:
                    seen_docs.add(doc_id)
                    relevant_docs.append({
                        "doc_id": doc_id,
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": getattr(doc, 'score', None)  # 如果有相似度分数
                    })

                    if len(relevant_docs) >= max_docs:
                        break

            return relevant_docs

        except Exception as e:
            logger.error(f"文档检索失败 {user_id}: {str(e)}")
            return []

    def _build_context(self, relevant_docs: List[Dict[str, Any]]) -> str:
        """
        构建问答上下文
        Args:
            relevant_docs: 相关文档列表
        Returns:
            上下文字符串
        """
        if not relevant_docs:
            return "无相关文档内容"

        context_parts = []
        for i, doc in enumerate(relevant_docs, 1):
            content = doc["content"].strip()
            doc_id = doc["doc_id"][:8]  # 截取文档ID前8位作为标识

            context_parts.append(f"[文档 {doc_id}]\n{content}")

        return "\n\n".join(context_parts)

    def _extract_sources(self, relevant_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        提取来源信息
        Args:
            relevant_docs: 相关文档列表
        Returns:
            来源信息列表
        """
        sources = []
        for doc in relevant_docs:
            metadata = doc.get("metadata", {})

            # 这里需要从数据库获取文档标题等信息
            # 暂时使用文档ID
            source = {
                "doc_id": doc["doc_id"],
                "title": f"文档 {doc['doc_id'][:8]}",  # 临时标题
                "relevance_score": doc.get("score") or 0.8,  # 默认相关度
                "chunk_count": 1
            }
            sources.append(source)

        return sources

    def _calculate_confidence(
        self,
        relevant_docs: List[Dict[str, Any]],
        question: str
    ) -> float:
        """
        计算回答置信度
        Args:
            relevant_docs: 相关文档
            question: 问题
        Returns:
            置信度分数 (0-1)
        """
        if not relevant_docs:
            return 0.0

        # 简单置信度计算
        base_confidence = min(len(relevant_docs) * 0.2, 0.8)  # 文档数量贡献

        # 检查问题关键词是否在文档中出现
        question_keywords = set(question.lower().split())
        total_matches = 0

        for doc in relevant_docs:
            content_lower = doc["content"].lower()
            matches = sum(1 for keyword in question_keywords if keyword in content_lower)
            total_matches += matches

        keyword_confidence = min(total_matches * 0.1, 0.2)  # 关键词匹配贡献

        return min(base_confidence + keyword_confidence, 1.0)

    def get_user_qa_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户问答统计
        Args:
            user_id: 用户ID
        Returns:
            统计信息
        """
        try:
            # 获取向量集合统计
            vector_stats = vector_manager.get_collection_stats(user_id)

            return {
                "total_documents": vector_stats.get("total_documents", 0),
                "total_vectors": vector_stats.get("total_vectors", 0),
                "collection_name": vector_stats.get("collection_name", ""),
                "qa_available": vector_stats.get("total_documents", 0) > 0
            }

        except Exception as e:
            logger.error(f"获取问答统计失败 {user_id}: {str(e)}")
            return {
                "total_documents": 0,
                "total_vectors": 0,
                "qa_available": False,
                "error": str(e)
            }

# 全局问答引擎实例
qa_engine = PersonalizedQAEngine()
