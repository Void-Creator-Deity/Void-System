from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import create_agent
from langchain.chat_models import ChatOpenAI

def load_advisor_chain():
    prompt = PromptTemplate(
        template="你是虚空学习系统的AI引导精灵，根据主题生成学习任务建议。\n主题：{topic}\n返回一条任务建议与奖励设定。",
        input_variables=["topic"],
    )
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.8)
    return LLMChain(llm=llm, prompt=prompt)
