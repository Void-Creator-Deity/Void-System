from langchain_classic.chains import ConversationChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_ollama import ChatOllama

def load_persona_chain():
    llm = ChatOllama(model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M", temperature=0.6)
    memory = ConversationBufferMemory()
    chain = ConversationChain(llm=llm, memory=memory)
    return chain
