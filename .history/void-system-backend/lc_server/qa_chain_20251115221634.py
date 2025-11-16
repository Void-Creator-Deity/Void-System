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

    # 3️⃣ 重新设计处理流程
    def create_qa_input(input_data):
        question = input_data["question"]
        return {
            "question": question,
            "context": retriever.invoke(question)
        }
    def debug_input(x):
        print(f"[QA链] 实际收到的输入: {x}, 类型: {type(x)}")
        return x

    #4️⃣ 构建处理链
    chain = (
        # RunnablePassthrough()
        # .assign(
        #     context=lambda x: retriever.invoke(x["question"]),
        #     question=lambda x: x["question"] 
        # ) # 接收原始输入
        RunnableLambda(debug_input)
        .assign(
            context=lambda x: retriever.invoke(x["question"]),
            question=lambda x: x["question"]
        ) 
        |RunnablePassthrough()
         .assign(
            context=lambda x: retriever.invoke(x["question"]),
            question=lambda x: x["question"] 
        ) # 接收原始输入
        # RunnableParallel({
        #     "context": lambda x: retriever.invoke(x["question"]),
        #     "question": lambda x: x["question"]}
        # )
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain
embeddings = OllamaEmbeddings(model="hf.co/Qwen/Qwen3-Embedding-4B-GGUF:Q8_0")
db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings
)
retriever = db.as_retriever(search_kwargs={"k": 3})
# if __name__ == "__main__":
#     # 测试管道
#     qa_chain = load_qa_chain()
#     test_question = "虚空系统的核心功能是什么？"
#     result = qa_chain.invoke({"question": test_question})
#     print(f"问：{test_question}\n答：{result}")
def test_input_schemas():
    # 测试 RunnableLambda 版本
    chain1 = RunnableLambda(lambda x: x).assign(
        context=lambda x: retriever.invoke(x["question"]),
        question=lambda x: x["question"]
    )
    print("RunnableLambda 输入模式:", chain1.input_schema.schema())
    
    # 测试 RunnablePassthrough 版本
    chain2 = RunnablePassthrough().assign(
        context=lambda x: retriever.invoke(x["question"]),
        question=lambda x: x["question"]
    )
    print("RunnablePassthrough 输入模式:", chain2.input_schema.schema())

test_input_schemas()
# 模拟 LangServe 的输入处理
# 模拟 LangServe 的输入处理
chain1 = RunnableLambda(lambda x: x).assign(
    context=lambda x: retriever.invoke(x["question"]),
    question=lambda x: x["question"]
)
print("RunnableLambda 输入模式:", chain1.input_schema.schema())

# 测试 RunnablePassthrough 版本
chain2 = RunnablePassthrough().assign(
    context=lambda x: retriever.invoke(x["question"]),
    question=lambda x: x["question"]
)
def simulate_langserve_input(chain, request_body):
    # LangServe 的处理逻辑
    body = request_body  # {"input": {"question": "..."}}
    input_data = body["input"]  # 提取出 {"question": "..."}
    
    # 传递给链
    return chain.invoke(input_data)

# 测试两个链
test_input = {"input": {"question": "测试问题"}}

result1 = simulate_langserve_input(chain1, test_input)
result2 = simulate_langserve_input(chain2, test_input)