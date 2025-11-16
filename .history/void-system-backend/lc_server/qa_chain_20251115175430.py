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

    # 3️⃣ 重构输入处理 - 使用 Runnable 链式处理
    def extract_question(input_data):
        """处理各种输入格式，提取问题字符串"""
        if isinstance(input_data, dict):
            # 处理 LangServe 的输入格式
            if "input" in input_data:
                inner_input = input_data["input"]
                if isinstance(inner_input, str):
                    return inner_input
                elif isinstance(inner_input, dict):
                    return inner_input.get("question", inner_input.get("text", str(inner_input)))
            # 处理直接的问题字段
            return input_data.get("question", input_data.get("text", str(input_data)))
        # 如果已经是字符串，直接返回
        elif isinstance(input_data, str):
            return input_data
        # 其他情况转换为字符串
        return str(input_data)

    # 4️⃣ 重新设计处理流程
    def create_qa_input(input_data):
        question = extract_question(input_data)
        return {
            "question": question,
            "context": retriever.get_relevant_documents(question)
        }

    # 5️⃣ 构建处理链
    chain = (
        RunnablePassthrough()  # 接收原始输入
        | RunnableLambda(create_qa_input)  # 转换为标准格式
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain