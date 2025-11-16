"""
Void System - QA Chain (LangChain v1+ Compatible)
------------------------------------------------
现代化 RAG 管道示例，用于知识检索 + 问答。
完全兼容 LangServe / FastAPI。
"""

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_classic.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


def load_qa_chain():
    """
    加载基于 LangChain v1 的检索问答管道
    """

    # 1️⃣ 定义模型与知识库
    embeddings = OllamaEmbeddings(model="hf.co/Qwen/Qwen3-Embedding-4B-GGUF:Q8_0")
    db = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embeddings
    )
    retriever = db.as_retriever(search_kwargs={"k": 3})

    llm = ChatOllama(model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M", temperature=0.5)

    # 2️⃣ 定义 Prompt 模板
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

    # 3️⃣ 定义数据流管道
    # Accept a simple string as input from the client (e.g. {"input": "..."})
    # and map it to the retriever and prompt pipeline.
    # Support two input shapes:
    # 1) simple string: {"input": "什么是LangChain？"}
    # 2) dict with question: {"input": {"question": "什么是LangChain？"}}
    def _extract_question(x):
        # If the incoming value is a dict, prefer 'question' then 'input'
        if isinstance(x, dict):
            if "question" in x and isinstance(x["question"], str):
                return x["question"]
            if "input" in x and isinstance(x["input"], str):
                return x["input"]
            # Fallback: try common fields
            for key in ("q", "text", "prompt"):
                if key in x and isinstance(x[key], str):
                    return x[key]
            # As a last resort, stringify the dict
            return str(x)
        # If it's already a string (or other scalar), return as-is
        return x

    chain = (
        RunnableParallel({
            "context": lambda x: retriever.invoke(x["question"]),
            "question": lambda x: x["question"],
        })
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain