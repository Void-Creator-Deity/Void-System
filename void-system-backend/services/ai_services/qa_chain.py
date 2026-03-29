"""
Void System - QA Chain (RAG Pipeline)
---------------------------------------
基于 LangChain 的检索增强生成（RAG）管道，用于知识库问答。
完全兼容 LangServe / FastAPI。
"""
from pathlib import Path
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
#from langchain_classic.prompts import ChatPromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, Any
from config import config
def load_qa_chain() -> Any:
    """
    加载基于 LangChain 的检索问答管道
    Returns:
        配置好的 RAG 问答链
    """
    # 初始化嵌入模型
    embeddings = OllamaEmbeddings(
        model=config.EMBEDDING_MODEL
    )
    # 确保 ChromaDB 持久化目录存在
    chroma_dir = Path("./chroma_db").resolve()
    chroma_dir.mkdir(parents=True, exist_ok=True)
    # 初始化向量数据库
    db = Chroma(
        persist_directory=str(chroma_dir),
        embedding_function=embeddings,
    )
    # 创建检索器（返回 top 3 相关文档）
    retriever = db.as_retriever(search_kwargs={"k": 3})
    # 初始化 LLM 模型
    llm = ChatOllama(
        model=config.CHAT_MODEL,
        temperature=0.3
    )

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
            
        all_docs = system_docs + user_docs
        
        # 按类型标注上下文
        context_parts = []
        for d in system_docs:
            context_parts.append(f"[系统知识库]: {d.page_content}")
        for d in user_docs:
            context_parts.append(f"[用户个人库]: {d.page_content}")
            
        return "\n\n".join(context_parts) if context_parts else "没有找到相关参考内容。"

    # 定义提示模板
    prompt = ChatPromptTemplate.from_template("""
    你是虚空系统的智能助手。
    目标：根据提供的【参考资料】回答【用户问题】。
    
    【参考资料】：
    {context}
    
    【用户问题】：
    {question}
    
    【指令】：
    1. 优先基于参考资料回答。资料包含系统知识库和用户个人库的内容。
    2. 如果资料内容不足，可以结合通用知识系统地回答，但需指明资料来源。
    3. 如果参考资料中完全没有相关信息，请告知无法从现有知识库中找到确切证据。
    4. 保持系统风格：克制、专业、逻辑化。
    5. 使用 Markdown 格式增强可读性。
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
