"""Planning context and mode policy shared by Growth App transports."""
import re
from typing import Any, Dict, List, Optional, Tuple


def build_generation_context(
    current_user: Dict[str, Any],
    user_capabilities: List[Dict[str, Any]],
    advisor_preferences: Optional[Dict[str, Any]] = None,
) -> str:
    capability_lines: List[str] = []
    for capability in user_capabilities:
        capability_id = str(capability.get("attr_id", "")).strip()
        name = str(capability.get("attr_name", "")).strip() or "未命名属性"
        description = str(capability.get("description", "")).strip()
        current = float(capability.get("attr_value", 0) or 0)
        maximum = max(float(capability.get("max_value", 100) or 100), 1.0)
        weakness = round(1.0 - max(0.0, min(1.0, current / maximum)), 3)
        capability_lines.append(
            f"- {name} (id={capability_id}, value={int(current)}/{int(maximum)}, "
            f"weakness={weakness}, desc={description or '无'})"
        )
    capabilities = "\n".join(capability_lines) if capability_lines else "- 无可用属性"

    specialization = str(current_user.get("specialization") or "").strip() or "未填写"
    learning_goal = str(current_user.get("learning_goal") or "").strip() or "未填写"
    preferences = advisor_preferences or {}
    response_style = str(preferences.get("response_style") or "").strip() or "专业"
    try:
        temperature = int(float(preferences.get("response_temperature", 35) or 35))
    except (TypeError, ValueError):
        temperature = 35
    temperature = max(0, min(100, temperature))

    return (
        "【用户画像（参考信号，非强制）】\n"
        f"- 专业方向: {specialization}\n"
        f"- 学习目标: {learning_goal}\n\n"
        "【用户偏好（可参考）】\n"
        f"- 回复风格: {response_style}\n"
        f"- 生成温度偏好(0~100): {temperature}\n\n"
        "【可用属性（含归一化弱项指标，仅供参考）】\n"
        f"{capabilities}\n\n"
        "【策略约束】\n"
        "- 任务主线必须优先贴合用户输入，不要被画像信息绑架。\n"
        "- 可适度照顾弱项（weakness 高），但仅在与任务语义相关时采用。\n"
        "- 若属性与任务明显无关，可输出空 related_attrs（{}），禁止强行挂靠。"
    )


def select_generation_mode(topic: str) -> Tuple[str, str]:
    text = (topic or "").strip().lower()
    if not text:
        return "workflow_chain", "empty_topic_default_workflow"

    workflow_keywords = [
        "路径", "计划", "学习路线", "任务链", "分解", "阶段", "长期", "路线", "大纲", "规划",
        "体系", "从零", "进阶", "项目", "训练营", "安排", "周期",
    ]
    single_keywords = [
        "单任务", "单个任务", "一个任务", "仅一个任务",
        "一步完成", "一步搞定", "一次性完成", "只要一步", "不要拆分",
    ]
    multi_clues = ["并且", "同时", "然后", "接着", "再", "；", ";", "，", ","]
    execution_keywords = ["背", "学习", "训练", "复习", "掌握", "提升", "完成", "刷题", "练习"]

    if any(keyword in text for keyword in single_keywords):
        return "single_task", "explicit_single_keyword"
    if any(keyword in text for keyword in workflow_keywords):
        return "workflow_chain", "workflow_keyword"
    if re.search(r"\d+", text) and any(keyword in text for keyword in execution_keywords):
        return "workflow_chain", "numeric_execution_goal"
    if len(text) >= 18:
        return "workflow_chain", "length_threshold"
    if sum(1 for clue in multi_clues if clue in text) >= 2:
        return "workflow_chain", "multi_clue_count"
    return "workflow_chain", "default_workflow"
