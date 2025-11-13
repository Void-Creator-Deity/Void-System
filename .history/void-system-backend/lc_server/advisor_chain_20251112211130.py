from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import LLMChain
from langchain_ollama import ChatOllama

def load_advisor_chain():
    prompt = PromptTemplate(
        template="你是虚空学习系统的AI引导精灵，根据主题生成学习任务建议。\n主题：{topic}\n返回一条任务建议与奖励设定。",
        input_variables=["topic"],
    )
    llm = ChatOllama(model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M", temperature=0.8)
    return create_agent(llm=llm, prompt=prompt)
