from langchain_ollama import ChatOllama
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables import RunnableLambda
import uuid

# 存储会话历史（可换 Redis）
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

    # ✅ 包装为带历史的 Runnable
    base_chain = RunnableWithMessageHistory(
        chain,
        get_history,
        input_messages_key="text",
        history_messages_key="history",
    )

    # ✅ 用 RunnableLambda 包装 “自动添加 session_id”
    def ensure_session(input_data, config=None):
        if config is None:
            config = {"configurable": {}}
        if "configurable" not in config:
            config["configurable"] = {}
        if "session_id" not in config["configurable"]:
            config["configurable"]["session_id"] = f"default-{uuid.uuid4().hex[:8]}"
        return base_chain.invoke(input_data, config=config)

    # ✅ 返回一个真正的 Runnable 对象
    return RunnableLambda(ensure_session)
