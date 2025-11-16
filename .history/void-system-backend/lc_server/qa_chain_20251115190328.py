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
from langchain_core.runnables import RunnableParallel, RunnablePassthrough,RunnableLambda
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

    # 3️⃣ 重构输入处理 - 使用 Runnable 链式处理
    def create_qa_input(input_data):
        question = input_data["question"]
        return {
            "question": question,
            "context": retriever.invoke(question)
        }
    def debug_input(x):
        print(f"[QA链] 实际收到的输入: {x}, 类型: {type(x)}")
        return x
    
    chain = (
        RunnablePassthrough()  # 先打印输入
        .assign(
            context=lambda x: retriever.invoke(x["question"]),
            question=lambda x: x["question"]
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain