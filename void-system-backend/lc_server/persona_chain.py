from langchain_ollama import ChatOllama
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.chat_history import BaseChatMessageHistory

# 模拟内存存储（后期可换 Redis）
store = {}

def get_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def load_persona_chain():
    llm = ChatOllama(model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M", temperature=0.5)

    prompt = ChatPromptTemplate.from_template("""
    你是系统精灵「VOID AI」，语气冷静、逻辑清晰。
    用户输入：{text}
    """)

    chain = prompt | llm

    # 新式对话链，带记忆
    return RunnableWithMessageHistory(
        chain,
        get_history,
        input_messages_key="text",
        history_messages_key="history",
    )
