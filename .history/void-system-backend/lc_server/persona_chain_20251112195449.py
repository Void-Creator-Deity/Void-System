from langchain_classic.chains import ConversationChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI 

def load_persona_chain():
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.6)
    memory = ConversationBufferMemory()
    chain = ConversationChain(llm=llm, memory=memory)
    return chain
