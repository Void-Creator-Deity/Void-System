from fastapi import FastAPI
from langserve import add_routes
from lc_server.qa_chain import load_qa_chain
from lc_server.advisor_chain import load_advisor_chain
from lc_server.persona_chain import load_persona_chain

app = FastAPI(title="Void System Core + LangServe")

# 注册 LangChain Server 模块
add_routes(app, load_qa_chain(), path="/lc/qa")
add_routes(app, load_advisor_chain(), path="/lc/advisor")
add_routes(app, load_persona_chain(), path="/lc/persona")

@app.get("/")
def read_root():
    return {"system": "VOID CORE ACTIVE"}
