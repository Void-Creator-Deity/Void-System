from langchain_ollama import ChatOllama
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.chat_history import BaseChatMessageHistory
import uuid

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

    persona_chain = RunnableWithMessageHistory(
        chain,
        get_history,
        input_messages_key="text",
        history_messages_key="history",
    )

    # ✅ 包装一个默认 session_id 的调用
    class PersonaChainWithDefault:
        def __init__(self, runnable):
            self.runnable = runnable
        async def ainvoke(self, input_data, config=None):
            if config is None:
                config = {"configurable": {"session_id": f"default-{uuid.uuid4().hex[:8]}"}}
            elif "configurable" not in config:
                config["configurable"] = {"session_id": f"default-{uuid.uuid4().hex[:8]}"}
            elif "session_id" not in config["configurable"]:
                config["configurable"]["session_id"] = f"default-{uuid.uuid4().hex[:8]}"
            return await self.runnable.ainvoke(input_data, config=config)
        def invoke(self, input_data, config=None):
            if config is None:
                config = {"configurable": {"session_id": f"default-{uuid.uuid4().hex[:8]}"}}
            elif "configurable" not in config:
                config["configurable"] = {"session_id": f"default-{uuid.uuid4().hex[:8]}"}
            elif "session_id" not in config["configurable"]:
                config["configurable"]["session_id"] = f"default-{uuid.uuid4().hex[:8]}"
            return self.runnable.invoke(input_data, config=config)

    return PersonaChainWithDefault(persona_chain)
