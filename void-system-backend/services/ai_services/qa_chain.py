"""
Void System - QA Chain (RAG Pipeline)
---------------------------------------
基于 LangChain 的检索增强生成（RAG）管道，用于知识库问答。
完全兼容 LangServe / FastAPI。
"""
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, Any
from config import config
from services.ai_services.llm_factory import get_chat_llm, get_embeddings

_qa_chain_singleton: Any = None


def load_qa_chain() -> Any:
    """
    加载基于 LangChain 的检索问答管道（进程内单例，避免每次 HTTP 请求重建 Chroma/嵌入模型）。
    Returns:
        配置好的 RAG 问答链
    """
    global _qa_chain_singleton
    if _qa_chain_singleton is None:
        _qa_chain_singleton = _build_qa_chain()
    return _qa_chain_singleton


def _build_qa_chain() -> Any:
    # 初始化嵌入模型（通过工厂，支持任意提供商）
    embeddings = get_embeddings()
    # 与文档向量、系统 RAG 管理器一致：锚定到后端包目录，避免依赖进程 cwd 读到另一份 chroma
    chroma_dir = config.get_chroma_path()
    chroma_dir.mkdir(parents=True, exist_ok=True)
    # 初始化向量数据库
    db = Chroma(
        persist_directory=str(chroma_dir),
        embedding_function=embeddings,
    )
    llm = get_chat_llm(temperature=0.3)

    # 定义混合检索逻辑
    def get_context(x: Dict[str, Any]) -> str:
        question = x["question"]
        mode = x.get("mode", "vector")
        user_id = x.get("user_id")
        
        system_docs = []
        user_docs = []
        
        # 系统知识库检索
        if mode == "hybrid":
            # 混合模式下获取更多的系统上下文
            system_docs = db.similarity_search(question, k=5)
            
            # 如果提供了用户ID，尝试获取用户个人文档内容
            if user_id:
                try:
                    # 动态导入避免循环依赖
                    from api.user_vector_manager import vector_manager
                    user_docs = vector_manager.search_user_documents(
                        user_id=user_id, 
                        query=question, 
                        top_k=5
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger("void-system-qa-chain")
                    logger.warning(f"混合模式检索用户文档失败: {e}")
        else:
            # 基础模式
            system_docs = db.similarity_search(question, k=3)

        # 按类型标注上下文
        context_parts = []
        for d in system_docs:
            context_parts.append(f"[系统知识库]: {d.page_content}")
        for d in user_docs:
            context_parts.append(f"[用户个人库]: {d.page_content}")
            
        return "\n\n".join(context_parts) if context_parts else "没有找到相关参考内容。"

    # 定义提示模板
    prompt = ChatPromptTemplate.from_template("""
    你是虚空系统知识问答助手，请依据资料回答用户问题。

    【参考资料】
    {context}

    【用户问题】
    {question}

    【回答规则】
    1) 优先使用参考资料作答，不要忽略资料中的关键信息。
    2) 若资料不足，可补充通用知识，但需明确标注“通用知识补充”。
    3) 若资料无法支持结论，必须明确说明“当前知识库证据不足”。
    4) 不编造文档内容，不伪造出处，不做无法验证的绝对结论。
    5) 输出使用简体中文，结构清晰，控制在务实风格。

    【输出结构（Markdown）】
    - 先给“结论”一段（1-3句）
    - 再给“依据”要点（优先引用参考资料中的关键信息）
    - 如存在不确定性，增加“限制与建议”小节
    """)

    def debug_input(x: Dict[str, Any]) -> Dict[str, Any]:
        return x

    # 构建处理链
    chain = (
        RunnableLambda(debug_input)
        .assign(
            context=get_context,
            question=lambda x: x["question"]
        )
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


if __name__ == "__main__":
    # 测试管道
    qa_chain = load_qa_chain()
    test_question = "虚空系统的核心功能是什么？"
    result = qa_chain.invoke({"question": test_question})
    print(f"问：{test_question}\n答：{result}")
