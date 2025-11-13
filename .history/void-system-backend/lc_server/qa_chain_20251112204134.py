from langchain_classic.chains import RetrievalQA
from langchain_ollama import ChatOllama, OllamaEmbeddings  # Corrected
from langchain_community.vectorstores import Chroma

def load_qa_chain():
    embeddings = OllamaEmbeddings(model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M")
    db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    retriever = db.as_retriever()
    llm = ChatOllama(model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M", temperature=0.7)
    chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
    return chain
