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
        temperature=0.3
    )

    # 定义混合检索逻辑
    def get_context(x: Dict[str, Any]) -> str:
        question = x["question"]
        mode = x.get("mode", "vector")
        
        if mode == "hybrid":
            # 尝试执行混合检索
            # 注意：BM25通常需要所有文档。为了简化，我们暂时使用Chroma的多模态检索或简单的向量检索加码
            # 这里我们通过增加k值并手动重排序来模拟混合检索的效果（或者如果支持BM25检索器则使用它）
            # 由于当前环境限制，我们先通过向量检索获取更多内容
            docs = db.similarity_search(question, k=6)
        else:
            docs = db.similarity_search(question, k=3)
            
        return "\n\n".join([d.page_content for d in docs])

    # 定义提示模板
    prompt = ChatPromptTemplate.from_template("""
    你是虚空系统的知识引擎。
    目标：根据【资料内容】精确回答【用户问题】。
    
    【资料内容】：
    {context}
    
    【用户问题】：
    {question}
    
    【指令】：
    1. 仅基于提供的资料回答。如果不确定，请告知无法从知识库中找到。
    2. 保持系统风格：克制、专业、逻辑化。
    3. 如果涉及技术、概念，请给出清晰的定义。
    4. 使用 Markdown 格式增强可读性。
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
