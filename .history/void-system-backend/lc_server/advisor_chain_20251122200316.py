"""
Void System - Advisor Chain (Learning Task Advisor)
-----------------------------------------------------
学习任务建议生成链，根据用户主题生成结构化的学习任务建议。
"""

from langchain_ollama import ChatOllama
from langchain_classic.prompts import PromptTemplate


def load_advisor_chain():
    """
    加载学习任务建议生成链
    
    Returns:
        配置好的任务建议生成链
    """
    # 定义提示模板
    prompt = PromptTemplate.from_template("""
    你是虚空学习系统的AI引导精灵。
    用户主题：{topic}
    
    请输出一个结构化的学习任务建议，包含：
    1. 任务标题
    2. 学习目标
    3. 建议时长
    4. 奖励提示
    
    请以清晰、有条理的方式组织你的回答。
    """)

    # 初始化 LLM 模型
    llm = ChatOllama(
        model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M",
        temperature=0.6
    )

    # 构建处理链：prompt → llm
    chain = prompt | llm
    
    return chain
