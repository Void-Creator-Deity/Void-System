from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chat_models import ChatOllama
from langchain_classic.chains import RetrievalQA

def load_qa_chain():
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    retriever = db.as_retriever()
    llm = ChatOllama(model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M", temperature=0.5)
    chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
    return chain
