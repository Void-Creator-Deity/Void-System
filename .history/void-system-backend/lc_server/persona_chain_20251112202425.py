from langchain_classic.chains import ConversationChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_ollama import ChatOllama

def load_persona_chain():
    llm = ChatOllama(model="gpt-3.5-turbo", temperature=0.6)
    memory = ConversationBufferMemory()
    chain = ConversationChain(llm=llm, memory=memory)
    return chain
