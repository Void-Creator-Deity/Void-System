"""
Void System - Structured Task Chain (任务结构化生成链)
-------------------------------------------------------
根据用户目标生成严格结构化的可执行任务，匹配前端JSON格式需求。
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
import json

# ==================== 1. 定义与前端完全匹配的数据结构 ====================
class TaskStep(BaseModel):
    """单个任务步骤，对应前端steps数组中的元素"""
    title: str = Field(description="步骤标题，如'阶段一：基础准备'")
    description: str = Field(description="步骤详细描述，具体要做什么")

class StructuredTaskPlan(BaseModel):
    """结构化任务计划，完全匹配前端期望的格式"""
    response: str = Field(
        description="对计划的简要总结性回应，如'基于您的目标，我已经为您完成了详细的任务计划。'",
        default="基于您的目标，我已经为您生成了详细的任务计划。"
    )
    steps: List[TaskStep] = Field(
        description="任务步骤数组，每个步骤包含title和description字段",
        min_items=3,
        max_items=6
    )
    estimatedDuration: str = Field(
        description="预估完成时间，如'45分钟'、'2周'、'每天1小时持续30天'",
        default="45分钟"
    )

# ==================== 2. 定义结构化生成链 ====================
def load_structured_task_chain() -> Runnable[Dict[str, Any], StructuredTaskPlan]:
    """
    加载结构化任务生成链
    返回可直接解析为StructuredTaskPlan对象的链
    """
    # 创建Pydantic输出解析器 - 强制模型输出指定格式
    parser = PydanticOutputParser(pydantic_object=StructuredTaskPlan)

    # 获取格式指令（会自动生成JSON格式说明）
    format_instructions = parser.get_format_instructions()

    # 定义包含格式指令的提示模板
    prompt = PromptTemplate(
        template="""
        你是虚空学习系统的AI引导精灵，专门为用户创建可执行、结构化的学习计划。

        ### 用户目标：
        {topic}

        ### 你的任务：
        根据用户目标，生成一个详细、可执行的任务计划。

        ### 输出格式要求：
        {format_instructions}

        ### 内容要求：
        1. **response字段**：一句友好的开场白，如"基于您的目标，我已经为您规划了以下学习路径："
        2. **steps字段**：这是核心！必须提供3-6个具体、可执行的步骤。
           - 每个步骤必须是独立、完整的行动指南
           - 步骤之间要有逻辑顺序（基础→进阶→实践）
           - 每个步骤的title要简洁明了，description要具体可行
        3. **estimatedDuration字段**：给出实际可行的总时间预估，如：
           - "4周（每周3次，每次1小时）"
           - "30小时（每天1小时，持续30天）"
           - "12节课（每节2小时）"

        ### 示例1：主题"学习Python编程"
        输出示例：
        {{
          "response": "基于您的目标，我已为您规划了Python编程的完整学习路径。",
          "steps": [
            {{"title": "阶段一：Python基础与环境搭建", "description": "安装Python环境，学习基础语法、数据类型和流程控制。"}},
            {{"title": "阶段二：面向对象编程", "description": "掌握类、对象、继承和多态等面向对象概念。"}},
            {{"title": "阶段三：项目实战练习", "description": "完成一个完整的Python项目，如网页爬虫或数据分析工具。"}},
            {{"title": "阶段四：高级特性学习", "description": "学习装饰器、生成器、异步编程等高级特性。"}}
          ],
          "estimatedDuration": "8周（每周6小时）"
        }}

        ### 示例2：主题"减肥塑形计划"
        输出示例：
        {{
          "response": "基于您的健身目标，我已为您制定了系统化的减肥塑形计划。",
          "steps": [
            {{"title": "阶段一：基础体测与习惯建立", "description": "进行身体基础数据测量，建立规律的饮食和运动习惯。"}},
            {{"title": "阶段二：有氧运动强化", "description": "进行跑步、游泳等有氧运动，每周4-5次，每次45分钟。"}},
            {{"title": "阶段三：力量训练加入", "description": "在有氧基础上加入力量训练，塑造肌肉线条。"}},
            {{"title": "阶段四：巩固与调整", "description": "根据身体反馈调整计划，巩固减肥成果。"}}
          ],
          "estimatedDuration": "12周（每周5次运动）"
        }}

        ### 现在，请为以下用户目标生成计划：
        用户目标：{topic}

        ### 重要提醒：
        - 输出必须是有效的JSON格式
        - 不要有任何额外的文本、Markdown标记或解释
        - steps数组必须有3-6个步骤
        - 每个步骤必须有title和description字段
        """,
        input_variables=["topic"],
        partial_variables={"format_instructions": format_instructions}
    )

    # 初始化 LLM 模型
    llm = ChatOllama(
        model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M",
        temperature=0.6,
        # 调整这些参数以获得更稳定的JSON输出
        top_p=0.9,
        frequency_penalty=0.1,
        presence_penalty=0.1
    )

    # 构建处理链：prompt -> llm -> 解析为结构化对象
    chain = prompt | llm | parser
    return chain

# ==================== 3. 备用方案：JSON输出解析器（更灵活） ====================
def load_json_task_chain() -> Runnable[Dict[str, Any], Dict]:
    """
    使用JsonOutputParser的备用方案，更灵活但稍欠严格
    """
    # 定义期望的JSON格式说明
    json_schema = {
        "type": "object",
        "properties": {
            "response": {"type": "string"},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["title", "description"]
                }
            },
            "estimatedDuration": {"type": "string"}
        },
        "required": ["response", "steps", "estimatedDuration"]
    }

    prompt = PromptTemplate.from_template("""
    你是虚空学习系统的AI引导精灵。
    用户目标：{topic}

    请生成一个结构化的学习任务计划，严格按照以下JSON格式输出：

    {{
      "response": "基于您的目标，我已经为您生成了详细的任务计划。",
      "steps": [
        {{"title": "步骤1标题", "description": "步骤1详细描述"}},
        {{"title": "步骤2标题", "description": "步骤2详细描述"}},
        {{"title": "步骤3标题", "description": "步骤3详细描述"}}
      ],
      "estimatedDuration": "总时长预估"
    }}

    要求：
    1. steps数组必须有3-5个步骤
    2. 每个步骤必须包含title和description字段
    3. estimatedDuration要具体可行
    4. 输出必须是纯JSON，不要有任何额外文本

    现在为这个目标生成计划：{topic}
    """)

    llm = ChatOllama(
        model="hf.co/unsloth/Qwen3-14B-GGUF:Q4_K_M",
        temperature=0.5  # 降低温度以获得更稳定的输出
    )

    # 使用JsonOutputParser
    json_parser = JsonOutputParser()

    chain = prompt | llm | json_parser
    return chain

# ==================== 4. 向后兼容的包装函数 ====================
def load_task_chain(use_structured: bool = True) -> Runnable:
    """
    向后兼容的加载函数
    参数：
        use_structured: 是否使用结构化输出（推荐True）
    """
    if use_structured:
        return load_structured_task_chain()
    else:
        return load_json_task_chain()

# ==================== 5. 错误处理与降级策略 ====================
def safe_invoke_chain(chain: Runnable, topic: str) -> Dict[str, Any]:
    """
    安全调用链，包含错误处理和降级策略
    特别处理包含<think>标签的响应，提取其中的JSON数据
    """
    import re

    # 净化AI响应，移除思考过程和内部指令
    def purify_ai_response(raw_content: str) -> str:
        """
        移除AI响应中的思考过程(如<think>标签)和内部指令
        """

        # 1. 移除整个<think>...</think>块及其内容
        purified = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL)

        # 2. 移除可能残留的"AI引导精灵"等内部角色提示
        purified = re.sub(r'^你是.*?精灵[。\n]*', '', purified)

        # 3. 提取JSON对象，处理可能的嵌套情况
        json_match = re.search(r'\{"response".*\}', purified, re.DOTALL)
        if json_match:
            purified = json_match.group(0)

        # 4. 清理多余的空行和首尾空白
        purified = purified.strip()

        return purified

    try:
        # 尝试直接调用链获取结果
        if hasattr(chain, 'invoke'):
            # 先尝试原始调用
            result = chain.invoke({"topic": topic})

            # 如果是Pydantic模型，转换为字典
            if hasattr(result, 'dict'):
                return result.dict()
            return result

    except Exception as e:
        print(f"结构化链调用失败: {e}")

        # 从错误信息中提取并净化JSON数据
        error_str = str(e)
        print(f"错误详情: {error_str}")

        # 净化错误信息，移除思考过程
        purified_error = purify_ai_response(error_str)

        # 尝试解析净化后的错误信息
        if purified_error:
            try:
                json_result = json.loads(purified_error)
                if isinstance(json_result, dict) and "response" in json_result and "steps" in json_result:
                    return json_result
            except json.JSONDecodeError:
                print(f"净化后的错误信息解析失败: {purified_error}")

        # 尝试在原始错误信息中查找JSON
        json_match = re.search(r'\{.*\}', error_str, re.DOTALL)
        if json_match:
            try:
                json_result = json.loads(json_match.group(0))
                if isinstance(json_result, dict) and "response" in json_result and "steps" in json_result:
                    return json_result
            except json.JSONDecodeError:
                print("从错误信息中提取JSON失败")

        # 降级策略：使用JSON链重试
        try:
            print("尝试使用JSON链作为降级方案...")
            json_chain = load_json_task_chain()
            result = json_chain.invoke({"topic": topic})

            # 验证结果结构
            if isinstance(result, dict) and "response" in result and "steps" in result:
                return result

        except Exception as json_error:
            print(f"JSON链也失败: {json_error}")

            # 净化JSON链错误信息
            json_error_str = str(json_error)
            purified_json_error = purify_ai_response(json_error_str)

            # 尝试解析净化后的JSON链错误信息
            if purified_json_error:
                try:
                    json_result = json.loads(purified_json_error)
                    if isinstance(json_result, dict) and "response" in json_result and "steps" in json_result:
                        return json_result
                except json.JSONDecodeError:
                    print(f"净化后的JSON链错误解析失败: {purified_json_error}")

            # 最终降级：返回一个默认结构
            return {
                "response": f"基于您的目标'{topic}'，我已经为您生成了详细的任务计划。",
                "steps": [
                    {"title": "第一阶段：基础知识学习", "description": "掌握核心概念和基础技能。"},
                    {"title": "第二阶段：实践应用训练", "description": "通过实际练习巩固所学知识。"},
                    {"title": "第三阶段：项目实战与总结", "description": "完成一个综合项目，总结学习成果。"}
                ],
                "estimatedDuration": "4周（根据个人进度调整）"
            }

    # 如果没有任何结果，返回默认结构
    return {
        "response": "基于您的目标，我已经为您生成了详细的任务计划。",
        "steps": [
            {"title": "第一阶段：规划与准备", "description": "明确学习目标，制定学习计划。"},
            {"title": "第二阶段：系统学习", "description": "按照计划进行系统学习。"},
            {"title": "第三阶段：实践与应用", "description": "通过实践巩固所学知识。"}
        ],
        "estimatedDuration": "45分钟"
    }
