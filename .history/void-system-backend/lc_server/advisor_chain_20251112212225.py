from langchain_ollama import ChatOllama
from langchain_classic.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

def load_advisor_chain():
    # 定义提示模板
    prompt = PromptTemplate.from_template("""
    你是虚空学习系统的AI引导精灵。
    用户主题：{topic}
    请输出一个结构化的学习任务建议，包含：
    1. 任务标题
    2. 学习目标
    3. 建议时长
    4. 奖励提示
    """)

    # 本地模型（改为你自己的模型）
    llm = ChatOllama(model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M", temperature=0.6)

    # 新版语法：prompt → llm 顺序管道
    chain = prompt | llm
    return chain
