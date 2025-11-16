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
from langchain_core.runnables import RunnablePassthrough,RunnableLambda,RunnableParallel
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

    # 3️⃣ 添加详细调试函数
    def debug_detailed(x):
        print(f"\n=== 详细调试信息 ===")
        print(f"[输入数据]: {x}")
        print(f"[输入类型]: {type(x)}")
        if isinstance(x, dict):
            print(f"[所有键]: {list(x.keys())}")
            for key, value in x.items():
                print(f"  {key}: {value} (类型: {type(value)})")
                if isinstance(value, dict):
                    print(f"    -> 嵌套键: {list(value.keys())}")
        print("==================\n")
        return x

    def debug_before_assign(x):
        print(f"[Before Assign] 输入: {x}")
        print(f"[Before Assign] 类型: {type(x)}")
        if isinstance(x, dict):
            print(f"[Before Assign] 键: {list(x.keys())}")
        return x

    def debug_after_assign(x):
        print(f"[After Assign] 输出: {x}")
        return x

    # 4️⃣ 构建处理链（带详细调试）
    chain = (
        RunnablePassthrough()
        | RunnableLambda(debug_detailed)  # 详细调试原始输入
        | RunnableLambda(debug_before_assign)  # 调试.assign之前的输入
        .assign(
            context=lambda x: retriever.invoke(x["question"]),
            question=lambda x: x["question"] 
        )
        | RunnableLambda(debug_after_assign)  # 调试.assign之后的输出
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain