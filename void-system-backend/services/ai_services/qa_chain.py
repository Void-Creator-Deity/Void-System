"""
Void System - QA Chain (RAG Pipeline)
---------------------------------------
基于 LangChain 的检索增强生成（RAG）管道，用于知识库问答。
完全兼容 LangServe / FastAPI。
"""
from pathlib import Path
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_classic.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, Any
def load_qa_chain() -> Any:
    """
    加载基于 LangChain 的检索问答管道
    Returns:
        配置好的 RAG 问答链
    """
    # 初始化嵌入模型
    embeddings = OllamaEmbeddings(
        model="hf.co/Qwen/Qwen3-Embedding-4B-GGUF:Q8_0"
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
        model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M",
        temperature=0.5
    )
    # 定义提示模板
    prompt = ChatPromptTemplate.from_template("""
    你是虚空系统的知识引擎。
    基于以下资料回答用户问题：
    ----------------
    {context}
    ----------------
    问题：{question}
    要求：
    - 逻辑清晰
    - 精简直接
    - 用系统风格回答（冷静、机械、精确）
    """)
    def debug_input(x: Dict[str, Any]) -> Dict[str, Any]:
        """
        调试输入（可选，用于开发阶段）
        Args:
            x: 输入数据
        Returns:
            原始输入数据
        """
        # 开发阶段可以启用调试输出
        # print(f"[QA链] 实际收到的输入: {x}, 类型: {type(x)}")
        return x
    # 构建处理链
    chain = (
        RunnableLambda(debug_input)
        .assign(
            context=lambda x: retriever.invoke(x["question"]),
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
