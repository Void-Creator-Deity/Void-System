from langchain_classic.chains import RetrievalQA
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # Corrected
from langchain_community.vectorstores import Chroma

def load_qa_chain():
    embeddings = OpenAIEmbeddings()
    db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    retriever = db.as_retriever()
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
    chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
    return chain
