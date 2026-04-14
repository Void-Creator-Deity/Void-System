"""
Void System - Task Generation & Evaluation
----------------------------------------
提供：
- 简单单任务：single-pass 生成
- 复杂任务链：三阶段工作流生成（大纲 -> 细化 -> 审校/清洗）
- AI 评判：evaluate_submission

重要：所有 LLM 输出均使用“提取 JSON + 容错解析”，避免 <think>/解释文本导致解析崩溃。
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import json
import re
import time
import hashlib
import logging
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser

from config import config
from services.ai_services.llm_factory import get_chat_llm
from langchain_ollama import ChatOllama

logger = logging.getLogger("void-system")


# ==================== Models ====================
class TaskStep(BaseModel):
    title: str = Field(description="任务节点标题")
    description: str = Field(description="任务节点详细描述")
    related_attrs: Dict[str, float] = Field(default_factory=dict, description="attr_id: weight")
    reward_coins: int = Field(default=20, ge=0, le=300)
    attribute_points: int = Field(default=0, ge=0, le=100)
    estimated_time: int = Field(default=30, ge=1, le=480)
    priority: str = Field(default="medium")
    task_type: str = Field(default="main")
    completion_type: str = Field(default="ai_eval")
    completion_criteria: Dict[str, Any] = Field(default_factory=dict)
    attribute_plan: List[Dict[str, Any]] = Field(default_factory=list)


class StructuredTaskPlan(BaseModel):
    response: str = Field(default="已生成任务链。")
    steps: List[TaskStep] = Field(min_items=1, max_items=8)
    estimatedDuration: str = Field(default="—")


class TaskEvaluationResult(BaseModel):
    status: str = Field(description="pass/fail")
    feedback: str
    score: int = Field(ge=0, le=100)
    suggested_rewards: Dict[str, int] = Field(default_factory=dict)


class OutlineStep(BaseModel):
    title: str
    purpose: str


class OutlinePlan(BaseModel):
    response: str
    outline_steps: List[OutlineStep] = Field(min_items=1, max_items=8)


class AttributeIntent(BaseModel):
    attr_key: str
    weight: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = Field(default="")


class WorkflowStepState(BaseModel):
    idx: int
    outline_step: Dict[str, Any]
    draft: Dict[str, Any] = Field(default_factory=dict)
    step_obj: Dict[str, Any] = Field(default_factory=dict)
    review_round: int = 0
    missing_keys: List[str] = Field(default_factory=list)
    repair_log: List[Dict[str, Any]] = Field(default_factory=list)
    key_timings: List[Dict[str, Any]] = Field(default_factory=list)
    stage2_ms: int = 0
    stage3_ms: int = 0
    ok: bool = False


class WorkflowRuntimeState(BaseModel):
    topic: str
    profile_context: str = ""
    user_attrs: List[Dict[str, Any]] = Field(default_factory=list)
    outline: Dict[str, Any] = Field(default_factory=dict)
    step_states: List[WorkflowStepState] = Field(default_factory=list)
    max_review_rounds: int = 3
    fallback: bool = False
    fallback_reason: str = ""
    debug_log: List[Dict[str, Any]] = Field(default_factory=list)
    key_cache: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, int] = Field(default_factory=lambda: {
        "llm_call_count": 0,
        "cache_hit_count": 0,
        "batch_call_count": 0,
    })


# ==================== JSON extraction helpers ====================
def _strip_think(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_json_object(text: str) -> str:
    """
    从任意文本中尽量提取一个 JSON 对象字符串。
    支持 ```json ...``` 或直接包含 {...}
    """
    if not text:
        raise ValueError("empty LLM output")
    t = _strip_think(text)
    # fenced
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", t, re.DOTALL)
    if m:
        return m.group(1).strip()
    # first {...} greedy but bounded by last }
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        return t[start : end + 1].strip()
    raise ValueError("no json object found")


def _invoke_llm_for_json(prompt: PromptTemplate, variables: Dict[str, Any], temperature: float, json_mode: bool) -> Dict[str, Any]:
    llm = get_chat_llm(temperature=temperature, json_mode=json_mode)
    rendered = prompt.format(**variables)
    # 直接 invoke 模型，拿 content 再手工提取 JSON，避免 parser 过早炸裂
    resp = llm.invoke(rendered)
    content = resp.content if hasattr(resp, "content") else str(resp)
    js = _extract_json_object(content)
    return json.loads(js)


# ==================== Chains ====================
def load_structured_task_chain() -> Runnable[Dict[str, Any], StructuredTaskPlan]:
    parser = PydanticOutputParser(pydantic_object=StructuredTaskPlan)
    format_instructions = parser.get_format_instructions()
    prompt = PromptTemplate(
        template="""
你是虚空系统任务顾问。把用户目标转成可执行任务链，并产出可直接落库字段。

【用户目标（主信号）】
{topic}

【用户画像与属性上下文（参考信号）】
{profile_context}

【输出格式要求】
{format_instructions}

【硬规则】
1) 只输出 JSON。
2) title/description 必须具体可执行。
3) related_attrs 只有语义相关才填；否则必须 {{}}。
4) 若 related_attrs 为空，则 attribute_points 必须为 0，attribute_plan 必须为 []。
5) completion_criteria 必须包含 criteria/deliverables/checks/pass_threshold/evidence，且 deliverables/checks/evidence 不得为空数组。
""",
        input_variables=["topic", "profile_context"],
        partial_variables={"format_instructions": format_instructions},
    )
    llm = get_chat_llm(temperature=0.7, json_mode=True)
    return prompt | llm | parser


def load_json_task_chain() -> Runnable[Dict[str, Any], Dict]:
    prompt = PromptTemplate.from_template("""
你是虚空系统任务顾问。输出必须为纯 JSON（不要解释、不要代码块）。

用户目标：{topic}
用户画像上下文（仅参考）：{profile_context}

输出 JSON 结构：
{{
  "response": "...",
  "steps": [
    {{
      "title": "...",
      "description": "...",
      "related_attrs": {{}},
      "reward_coins": 20,
      "attribute_points": 0,
      "estimated_time": 30,
      "priority": "medium",
      "task_type": "main",
      "completion_type": "ai_eval",
      "completion_criteria": {{
        "criteria": "...",
        "deliverables": ["...","..."],
        "checks": ["...","..."],
        "pass_threshold": "由评分AI综合判定",
        "evidence": ["...","..."]
      }}
    }}
  ],
  "estimatedDuration": "—"
}}
""")
    llm = get_chat_llm(temperature=0.5, json_mode=False)
    json_parser = JsonOutputParser()
    return prompt | llm | json_parser


def load_task_chain(use_structured: bool = True) -> Runnable:
    return load_structured_task_chain() if use_structured else load_json_task_chain()


# ==================== Attribute inference & plan preview ====================
def _infer_related_attrs_from_task_text(step: Dict[str, Any], user_attrs: List[Dict[str, Any]]) -> Dict[str, float]:
    title = str(step.get("title", "")).strip().lower()
    description = str(step.get("description", "")).strip().lower()
    text = f"{title} {description}"
    if not text.strip():
        return {}
    scored: List[Tuple[str, float]] = []
    for attr in user_attrs:
        attr_id = str(attr.get("attr_id", "")).strip()
        if not attr_id:
            continue
        name = str(attr.get("attr_name", "")).strip().lower()
        desc = str(attr.get("description", "")).strip().lower()
        tokens = [t for t in [name, desc] if t]
        score = 0.0
        for tok in tokens:
            if tok and tok in text:
                score += 1.0
        if score > 0:
            scored.append((attr_id, score))
    if not scored:
        return {}
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:2]
    total = sum(s for _, s in top) or 1.0
    return {attr_id: round(score / total, 3) for attr_id, score in top}


def _calc_attr_reward_distribution(task_like: Dict[str, Any], user_attrs: List[Dict[str, Any]], score_factor: float = 1.0) -> Dict[str, int]:
    related = task_like.get("related_attrs") or {}
    if not isinstance(related, dict) or not related:
        return {}
    attr_ids = {a.get("attr_id") for a in user_attrs if a.get("attr_id")}
    valid_items: List[Tuple[str, float]] = []
    for attr_id, weight in related.items():
        if attr_id in attr_ids and isinstance(weight, (int, float)) and weight > 0:
            valid_items.append((attr_id, float(weight)))
    if not valid_items:
        return {}
    base_points = int(task_like.get("attribute_points") or 0)
    total_points = int(max(0, round(base_points * max(0.1, score_factor))))
    if total_points <= 0:
        return {}
    weight_sum = sum(w for _, w in valid_items) or 1.0
    raw_alloc = [(attr_id, total_points * w / weight_sum) for attr_id, w in valid_items]
    distribution: Dict[str, int] = {}
    floors = 0
    remainders: List[Tuple[float, str]] = []
    for attr_id, raw in raw_alloc:
        f = int(raw)
        distribution[attr_id] = f
        floors += f
        remainders.append((raw - f, attr_id))
    remain = total_points - floors
    if remain > 0:
        remainders.sort(reverse=True)
        for _, aid in remainders[:remain]:
            distribution[aid] += 1
    return {k: v for k, v in distribution.items() if v > 0}


def _build_attribute_plan_preview(distribution: Dict[str, int], user_attrs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not distribution:
        return []
    name_map = {a.get("attr_id"): a.get("attr_name") for a in user_attrs if a.get("attr_id")}
    out = []
    for aid, pts in distribution.items():
        if pts <= 0:
            continue
        out.append({"attr_id": aid, "attr_name": name_map.get(aid) or aid, "points": int(pts)})
    return out


def _build_related_attrs_detail(related_attrs: Dict[str, float], user_attrs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(related_attrs, dict) or not related_attrs:
        return []
    attr_map = {str(a.get("attr_id")): a for a in user_attrs if a.get("attr_id")}
    detail: List[Dict[str, Any]] = []
    for attr_id, weight in related_attrs.items():
        row = attr_map.get(str(attr_id))
        if not row:
            continue
        try:
            w = float(weight)
        except Exception:
            continue
        if w <= 0:
            continue
        detail.append({
            "attr_id": str(attr_id),
            "attr_name": row.get("attr_name") or str(attr_id),
            "attr_description": row.get("description") or "",
            "weight": round(w, 3),
        })
    detail.sort(key=lambda x: x["weight"], reverse=True)
    return detail


def _attribute_intent_plan(step_like: Dict[str, Any], user_attrs: List[Dict[str, Any]]) -> List[AttributeIntent]:
    """
    Plan机制第一段：先给出候选属性意图（含理由），避免直接分配造成黑盒。
    """
    title = str(step_like.get("title", "")).strip()
    desc = str(step_like.get("description", "")).strip()
    if not user_attrs or not (title or desc):
        return []
    attrs_payload = [
        {
            "attr_id": str(a.get("attr_id")),
            "attr_name": a.get("attr_name") or "",
            "attr_description": a.get("description") or "",
        }
        for a in user_attrs
        if a.get("attr_id")
    ]
    # 语义优先：让模型输出候选属性意图；若失败再回退规则匹配
    try:
        prompt = PromptTemplate.from_template("""
你是任务属性语义规划器。请判断任务与给定属性的关联强度。

任务标题：{title}
任务描述：{description}
可用属性列表（仅能从中选择）：{attrs_json}

输出严格JSON：
{{
  "intents": [
    {{"attr_key": "attr_id", "weight": 0.0, "reason": "..." }}
  ]
}}

规则：
1) attr_key 必须是可用属性中的 attr_id（优先）或 attr_name。
2) weight 范围 0~1，仅保留最相关的1~3项；若都不相关返回空数组。
3) 不要输出其它字段与解释文本。
""")
        raw = _invoke_llm_for_json(
            prompt,
            {"title": title, "description": desc, "attrs_json": json.dumps(attrs_payload, ensure_ascii=False)},
            temperature=0.2,
            json_mode=True,
        )
        intents_raw = raw.get("intents") if isinstance(raw, dict) else []
        intents: List[AttributeIntent] = []
        if isinstance(intents_raw, list):
            for row in intents_raw[:5]:
                if not isinstance(row, dict):
                    continue
                key = str(row.get("attr_key", "")).strip()
                if not key:
                    continue
                try:
                    w = float(row.get("weight", 0.0) or 0.0)
                except Exception:
                    w = 0.0
                if w <= 0:
                    continue
                intents.append(
                    AttributeIntent(
                        attr_key=key,
                        weight=max(0.0, min(1.0, w)),
                        reason=str(row.get("reason", "")).strip()[:120],
                    )
                )
        if intents:
            return intents
    except Exception:
        pass

    inferred = _infer_related_attrs_from_task_text(step_like, user_attrs)
    intents_fb: List[AttributeIntent] = []
    name_map = {str(a.get("attr_id")): a.get("attr_name") or str(a.get("attr_id")) for a in user_attrs if a.get("attr_id")}
    for attr_id, weight in inferred.items():
        intents_fb.append(
            AttributeIntent(
                attr_key=str(attr_id),
                weight=float(weight),
                reason=f"规则回退：任务「{title or '当前步骤'}」与属性「{name_map.get(str(attr_id), str(attr_id))}」词面相关",
            )
        )
    return intents_fb


def _attribute_resolution(intents: List[AttributeIntent], user_attrs: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Plan机制第二段：将候选映射到真实用户属性ID并归一化权重。
    """
    if not intents:
        return {}
    attr_ids = {str(a.get("attr_id")) for a in user_attrs if a.get("attr_id")}
    name_to_id = {str(a.get("attr_name", "")).strip().lower(): str(a.get("attr_id")) for a in user_attrs if a.get("attr_id")}
    merged: Dict[str, float] = {}
    for intent in intents:
        key = str(intent.attr_key or "").strip()
        if not key:
            continue
        mapped = key if key in attr_ids else name_to_id.get(key.lower())
        if not mapped:
            continue
        merged[mapped] = merged.get(mapped, 0.0) + max(0.0, float(intent.weight or 0.0))
    total = sum(merged.values()) or 0.0
    if total <= 0:
        return {}
    return {k: round(v / total, 3) for k, v in merged.items() if v > 0}


def _attribute_distribution(related_attrs: Dict[str, float], attribute_points: int, user_attrs: List[Dict[str, Any]]) -> Tuple[int, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Plan机制第三段：根据related_attrs分配点数并产出明细。
    """
    dist = _calc_attr_reward_distribution({"related_attrs": related_attrs, "attribute_points": attribute_points}, user_attrs, 1.0)
    attr_plan = _build_attribute_plan_preview(dist, user_attrs)
    if not attr_plan:
        attr_plan = [{"attr_id": "none", "attr_name": "无", "points": 0}]
    points = sum(int(x.get("points", 0) or 0) for x in attr_plan if x.get("attr_id") != "none")
    detail = _build_related_attrs_detail(related_attrs, user_attrs)
    return points, attr_plan, detail


def _default_step_completion_criteria(topic: str, title: str, description: str) -> Dict[str, Any]:
    return {
        "criteria": f"完成《{title}》并提交可核验证据，产出需与「{topic}」目标一致。",
        "deliverables": ["执行记录或笔记", "可核验的成果物（截图/文件/链接等）"],
        "checks": ["产出与任务描述一致", "关键步骤可追溯"],
        "pass_threshold": "由评分AI综合判定",
        "evidence": ["截图", "文本说明", "日志或操作记录"],
    }


# ==================== Sanitizer (Stage3) ====================
def _sanitize_generated_plan(plan: Dict[str, Any], topic: str, user_attrs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(plan, dict):
        raise ValueError("plan is not dict")
    steps = plan.get("steps") or []
    if not isinstance(steps, list):
        steps = []
    normalized = []
    concise = (topic or "").splitlines()[0][:36] or "当前目标"
    for step in steps:
        if not isinstance(step, dict):
            continue
        title = str(step.get("title", "")).strip()
        desc = str(step.get("description", "")).strip()
        if not title or not desc:
            continue

        related = step.get("related_attrs")
        related = related if isinstance(related, dict) else {}

        # numbers
        def _to_int(v, default=0):
            try:
                return int(float(v))
            except Exception:
                return default

        reward = max(0, _to_int(step.get("reward_coins", 0), 0))
        minutes = _to_int(step.get("estimated_time", 30), 30)
        if minutes < 1:
            minutes = 30
        minutes = min(480, minutes)

        attr_points = max(0, _to_int(step.get("attribute_points", 0), 0))
        if not related and user_attrs:
            intents = _attribute_intent_plan({"title": title, "description": desc}, user_attrs)
            related = _attribute_resolution(intents, user_attrs)
            if related and attr_points == 0:
                attr_points = 6
        if attr_points > 0 and not related:
            attr_points = 0

        cc = step.get("completion_criteria")
        cc = cc if isinstance(cc, dict) else {}
        defaults = _default_step_completion_criteria(concise, title, desc)
        for k in ("criteria", "deliverables", "checks", "pass_threshold", "evidence"):
            v = cc.get(k)
            if v in (None, "", []) or k not in cc:
                cc[k] = defaults[k]
        points, attr_plan, related_detail = _attribute_distribution(related, attr_points, user_attrs)
        cc["attribute_plan"] = attr_plan

        normalized.append({
            "title": title,
            "description": desc,
            "related_attrs": related,
            "reward_coins": reward,
            "attribute_points": points,
            "estimated_time": minutes,
            "priority": step.get("priority") or "medium",
            "task_type": step.get("task_type") or "main",
            "completion_type": step.get("completion_type") or "ai_eval",
            "completion_criteria": cc,
            "attribute_plan": cc.get("attribute_plan") or [],
            "related_attrs_detail": related_detail,
        })

    plan["steps"] = normalized
    return plan


# ==================== Workflow generation ====================
def _stage1_outline(topic: str, profile_context: str) -> Dict[str, Any]:
    parser = PydanticOutputParser(pydantic_object=OutlinePlan)
    prompt = PromptTemplate(
        template="""
你是虚空系统任务顾问。先输出“任务链方向与大纲”，不要写完整细节。

【目标】
{topic}

【用户画像与属性上下文（仅参考）】
{profile_context}

【输出格式要求】
{format_instructions}

只输出 JSON。
""",
        input_variables=["topic", "profile_context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    # Stage1 容错：先尝试两次结构化生成，仍失败则返回最小可用大纲（不让流程直接崩盘）
    last_err = None
    for _ in range(2):
        try:
            result = _invoke_llm_for_json(
                prompt,
                {"topic": topic, "profile_context": profile_context},
                temperature=0.5,
                json_mode=True,
            )
            osteps = result.get("outline_steps") or result.get("outlineSteps") or []
            if isinstance(osteps, list) and len(osteps) > 0:
                return result
            last_err = ValueError("outline_steps missing")
        except Exception as e:
            last_err = e
    return {
        "response": f"大纲生成不稳定，已启用最小可用大纲：{str(last_err) if last_err else 'unknown'}",
        "outline_steps": [
            {"title": "明确目标与交付物", "purpose": f"围绕「{topic}」确定可验证产出与完成标准"},
            {"title": "执行并提交证据", "purpose": "按清单执行关键动作并提交可核验证据"},
        ],
        "estimatedDuration": "—",
    }


def _invoke_llm_text(prompt: str, temperature: float = 0.6) -> str:
    llm = get_chat_llm(temperature=temperature, json_mode=False)
    resp = llm.invoke(prompt)
    content = resp.content if hasattr(resp, "content") else str(resp)
    return _strip_think(content).strip()


def _cache_key(topic: str, title: str, key_name: str, profile_context: str) -> str:
    src = f"{topic}|{title}|{key_name}|{profile_context}"
    return hashlib.sha1(src.encode("utf-8")).hexdigest()


def _parse_int_text(text: str, default: int) -> int:
    m = re.search(r"-?\d+", text or "")
    if not m:
        return default
    try:
        return int(m.group(0))
    except Exception:
        return default


def _parse_list_text(text: str) -> List[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    lines = [ln.strip(" -•\t") for ln in raw.splitlines() if ln.strip()]
    if len(lines) == 1 and ("；" in lines[0] or ";" in lines[0] or "、" in lines[0]):
        split = re.split(r"[；;、]", lines[0])
        return [s.strip() for s in split if s.strip()]
    return lines


def _parse_related_attrs_text(text: str, user_attrs: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    输入示例：
    - attr_xxx:0.7, attr_yyy:0.3
    - 无
    """
    t = (text or "").strip()
    if not t or t in {"无", "none", "None", "{}"}:
        return {}
    attr_ids = {a.get("attr_id") for a in user_attrs if a.get("attr_id")}
    name_to_id = {str(a.get("attr_name", "")).strip().lower(): a.get("attr_id") for a in user_attrs if a.get("attr_id")}
    pairs = re.split(r"[,，\n]", t)
    out: Dict[str, float] = {}
    for p in pairs:
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        key = k.strip()
        try:
            w = float(v.strip())
        except Exception:
            continue
        if w <= 0:
            continue
        mapped = key if key in attr_ids else name_to_id.get(key.lower())
        if mapped:
            out[mapped] = max(0.1, min(1.0, w))
    return out


def generate_key_value(
    key_name: str,
    topic: str,
    profile_context: str,
    draft_step: Dict[str, Any],
    user_attrs: List[Dict[str, Any]],
    runtime_state: Optional[WorkflowRuntimeState] = None,
) -> Any:
    title = draft_step.get("title", "")
    purpose = draft_step.get("purpose", "")
    desc = draft_step.get("description", "")
    attrs_hint = ", ".join([f"{a.get('attr_name')}({a.get('attr_id')})" for a in user_attrs if a.get("attr_id")]) or "无"

    common = (
        f"总体目标：{topic}\n"
        f"节点标题：{title}\n"
        f"节点目的：{purpose}\n"
        f"已有描述：{desc}\n"
        f"可用属性（名称+id）：{attrs_hint}\n"
    )

    ck = _cache_key(topic, str(title), key_name, profile_context)
    if runtime_state is not None and ck in runtime_state.key_cache:
        runtime_state.metrics["cache_hit_count"] = runtime_state.metrics.get("cache_hit_count", 0) + 1
        return runtime_state.key_cache[ck]

    if key_name == "description":
        txt = _invoke_llm_text(
            common + "请只输出该任务节点的详细可执行描述（60~180字），不要输出JSON。", temperature=0.7
        )
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = txt
        return txt
    if key_name == "task_type":
        txt = _invoke_llm_text(common + "在 main/side/daily 中选一个最合适的，只输出一个词。", temperature=0.3)
        t = txt.lower().strip()
        out = t if t in {"main", "side", "daily"} else "main"
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "priority":
        txt = _invoke_llm_text(common + "在 easy/medium/hard 中选一个最合适的，只输出一个词。", temperature=0.3)
        p = txt.lower().strip()
        out = p if p in {"easy", "medium", "hard"} else "medium"
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "estimated_time":
        n = _parse_int_text(_invoke_llm_text(common + "输出预计分钟数（整数，1~480），只输出数字。", temperature=0.2), 30)
        out = max(1, min(480, n))
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "reward_coins":
        n = _parse_int_text(_invoke_llm_text(common + "输出系统币奖励（整数，0~300），只输出数字。", temperature=0.2), 20)
        out = max(0, min(300, n))
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "related_attrs":
        txt = _invoke_llm_text(
            common + "若有相关属性，请输出“attr_id:weight”列表（逗号分隔）；若无合适属性输出“无”。", temperature=0.5
        )
        out = _parse_related_attrs_text(txt, user_attrs)
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "attribute_points":
        if not draft_step.get("related_attrs"):
            return 0
        n = _parse_int_text(_invoke_llm_text(common + "输出属性成长点（整数，1~20），只输出数字。", temperature=0.2), 6)
        out = max(1, min(20, n))
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "completion_criteria.criteria":
        out = _invoke_llm_text(common + "输出一条任务达成标准（文本），不要JSON。", temperature=0.5)
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "completion_criteria.deliverables":
        out = _parse_list_text(_invoke_llm_text(common + "输出至少2条需要提交的产出物，每行一条。", temperature=0.5))
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "completion_criteria.checks":
        out = _parse_list_text(_invoke_llm_text(common + "输出至少2条检查项，每行一条。", temperature=0.5))
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "completion_criteria.pass_threshold":
        out = _invoke_llm_text(common + "输出通过判定规则一句话，不要JSON。", temperature=0.4)
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    if key_name == "completion_criteria.evidence":
        out = _parse_list_text(_invoke_llm_text(common + "输出至少2条可接受证据类型，每行一条。", temperature=0.5))
        if runtime_state is not None:
            runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
            runtime_state.key_cache[ck] = out
        return out
    return None


def generate_batch_core_fields(
    topic: str,
    profile_context: str,
    draft_step: Dict[str, Any],
    runtime_state: Optional[WorkflowRuntimeState] = None,
) -> Dict[str, Any]:
    title = str(draft_step.get("title", "")).strip()
    purpose = str(draft_step.get("purpose", "")).strip()
    desc = str(draft_step.get("description", "")).strip()
    ck = _cache_key(topic, title, "batch_core_fields", profile_context)
    if runtime_state is not None and ck in runtime_state.key_cache:
        runtime_state.metrics["cache_hit_count"] = runtime_state.metrics.get("cache_hit_count", 0) + 1
        val = runtime_state.key_cache[ck]
        return val if isinstance(val, dict) else {}

    prompt = PromptTemplate.from_template("""
你是任务字段生成器。请基于目标与步骤信息，输出一个严格JSON对象，只包含以下字段：
- task_type: main/side/daily
- priority: easy/medium/hard
- estimated_time: 1~480 的整数
- reward_coins: 0~300 的整数

目标：{topic}
步骤标题：{title}
步骤目的：{purpose}
已有描述：{description}
用户画像上下文：{profile_context}
""")
    result = _invoke_llm_for_json(
        prompt,
        {
            "topic": topic,
            "title": title,
            "purpose": purpose,
            "description": desc,
            "profile_context": profile_context,
        },
        temperature=0.2,
        json_mode=True,
    )
    out = {
        "task_type": result.get("task_type"),
        "priority": result.get("priority"),
        "estimated_time": result.get("estimated_time"),
        "reward_coins": result.get("reward_coins"),
    }
    if runtime_state is not None:
        runtime_state.metrics["llm_call_count"] = runtime_state.metrics.get("llm_call_count", 0) + 1
        runtime_state.metrics["batch_call_count"] = runtime_state.metrics.get("batch_call_count", 0) + 1
        runtime_state.key_cache[ck] = out
    return out


def build_step_draft_serial(
    topic: str,
    profile_context: str,
    outline_step: Dict[str, Any],
    user_attrs: List[Dict[str, Any]],
    runtime_state: Optional[WorkflowRuntimeState] = None,
) -> Dict[str, Any]:
    draft = {
        "title": str(outline_step.get("title", "")).strip() or "任务节点",
        "purpose": str(outline_step.get("purpose", "")).strip(),
        "completion_type": "ai_eval",
    }
    key_order = [
        "description",
        "related_attrs",
        "attribute_points",
        "completion_criteria.criteria",
        "completion_criteria.deliverables",
        "completion_criteria.checks",
        "completion_criteria.pass_threshold",
        "completion_criteria.evidence",
    ]
    key_timings: List[Dict[str, Any]] = []
    t_batch = time.perf_counter()
    batch_fields = generate_batch_core_fields(topic, profile_context, draft, runtime_state=runtime_state)
    key_timings.append({"key": "batch_core_fields", "elapsed_ms": int((time.perf_counter() - t_batch) * 1000)})
    for key in ("task_type", "priority", "estimated_time", "reward_coins"):
        if key in batch_fields and batch_fields.get(key) is not None:
            draft[key] = batch_fields.get(key)
    for key in key_order:
        t0 = time.perf_counter()
        value = generate_key_value(key, topic, profile_context, draft, user_attrs, runtime_state=runtime_state)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        key_timings.append({"key": key, "elapsed_ms": elapsed_ms})
        if key.startswith("completion_criteria."):
            cc_key = key.split(".", 1)[1]
            draft.setdefault("completion_criteria", {})[cc_key] = value
        else:
            draft[key] = value
    draft["_key_timings"] = key_timings
    return draft


def normalize_step_draft(draft: Dict[str, Any], topic: str, user_attrs: List[Dict[str, Any]]) -> Dict[str, Any]:
    title = str(draft.get("title", "")).strip() or "任务节点"
    desc = str(draft.get("description", "")).strip() or "无"
    related = draft.get("related_attrs")
    related = related if isinstance(related, dict) else {}

    def _to_int(v, default=0):
        try:
            return int(float(v))
        except Exception:
            return default

    minutes = max(1, min(480, _to_int(draft.get("estimated_time", 30), 30)))
    reward = max(0, min(300, _to_int(draft.get("reward_coins", 20), 20)))
    attr_points = max(0, min(100, _to_int(draft.get("attribute_points", 0), 0)))
    if not related and user_attrs:
        intents = _attribute_intent_plan({"title": title, "description": desc}, user_attrs)
        related = _attribute_resolution(intents, user_attrs)
        if related and attr_points == 0:
            attr_points = 6
    if not related:
        attr_points = 0

    cc = draft.get("completion_criteria")
    cc = cc if isinstance(cc, dict) else {}
    defaults = _default_step_completion_criteria((topic or "")[:36] or "当前目标", title, desc)
    for k in ("criteria", "deliverables", "checks", "pass_threshold", "evidence"):
        v = cc.get(k)
        if v in (None, "", []) or k not in cc:
            cc[k] = defaults[k]
    # 空语义：无
    if isinstance(cc.get("deliverables"), list) and not cc["deliverables"]:
        cc["deliverables"] = ["无"]
    if isinstance(cc.get("checks"), list) and not cc["checks"]:
        cc["checks"] = ["无"]
    if isinstance(cc.get("evidence"), list) and not cc["evidence"]:
        cc["evidence"] = ["无"]
    if not cc.get("pass_threshold"):
        cc["pass_threshold"] = "无"

    attr_points, attr_plan, related_detail = _attribute_distribution(related, attr_points, user_attrs)
    cc["attribute_plan"] = attr_plan

    return {
        "title": title,
        "description": desc,
        "related_attrs": related,
        "reward_coins": reward,
        "attribute_points": attr_points,
        "estimated_time": minutes,
        "priority": draft.get("priority") if draft.get("priority") in {"easy", "medium", "hard"} else "medium",
        "task_type": draft.get("task_type") if draft.get("task_type") in {"main", "side", "daily"} else "main",
        "completion_type": "ai_eval",
        "completion_criteria": cc,
        "attribute_plan": attr_plan,
        "related_attrs_detail": related_detail,
    }


def review_and_repair_keys(
    step_obj: Dict[str, Any],
    topic: str,
    profile_context: str,
    user_attrs: List[Dict[str, Any]],
    runtime_state: Optional[WorkflowRuntimeState] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    repaired = dict(step_obj)
    issues: List[str] = []
    # 审查关键字段
    if not str(repaired.get("description", "")).strip() or repaired.get("description") == "无":
        issues.append("description")
    if int(repaired.get("estimated_time", 0) or 0) < 1:
        issues.append("estimated_time")
    if repaired.get("priority") not in {"easy", "medium", "hard"}:
        issues.append("priority")
    if repaired.get("task_type") not in {"main", "side", "daily"}:
        issues.append("task_type")
    cc = repaired.get("completion_criteria") or {}
    for k in ("criteria", "deliverables", "checks", "pass_threshold", "evidence"):
        v = cc.get(k)
        if v in (None, "", []) or (isinstance(v, list) and len(v) == 0):
            issues.append(f"completion_criteria.{k}")
    ap = int(repaired.get("attribute_points", 0) or 0)
    ap_sum = sum(int(x.get("points", 0) or 0) for x in (repaired.get("attribute_plan") or []) if x.get("attr_id") != "none")
    if ap != ap_sum:
        issues.append("attribute_points")

    if not issues:
        return True, [], repaired

    # 定点重试缺失/不合规 key（串行）
    draft = {
        "title": repaired.get("title"),
        "purpose": "",
        "description": repaired.get("description"),
        "task_type": repaired.get("task_type"),
        "priority": repaired.get("priority"),
        "estimated_time": repaired.get("estimated_time"),
        "reward_coins": repaired.get("reward_coins"),
        "related_attrs": repaired.get("related_attrs"),
        "attribute_points": repaired.get("attribute_points"),
        "completion_criteria": repaired.get("completion_criteria", {}),
    }
    for issue in issues:
        if issue == "attribute_points":
            # 交给 normalize 统一重算，不单独重生
            continue
        val = generate_key_value(issue, topic, profile_context, draft, user_attrs, runtime_state=runtime_state)
        if issue.startswith("completion_criteria."):
            cc_key = issue.split(".", 1)[1]
            draft.setdefault("completion_criteria", {})[cc_key] = val
        else:
            draft[issue] = val
    repaired = normalize_step_draft(draft, topic, user_attrs)
    # 再次检查
    cc2 = repaired.get("completion_criteria") or {}
    ok = (
        bool(str(repaired.get("description", "")).strip())
        and int(repaired.get("estimated_time", 0) or 0) >= 1
        and repaired.get("priority") in {"easy", "medium", "hard"}
        and repaired.get("task_type") in {"main", "side", "daily"}
        and cc2.get("criteria") not in ("", None)
        and isinstance(cc2.get("deliverables"), list) and len(cc2.get("deliverables")) > 0
        and isinstance(cc2.get("checks"), list) and len(cc2.get("checks")) > 0
        and isinstance(cc2.get("evidence"), list) and len(cc2.get("evidence")) > 0
    )
    return ok, issues, repaired


def _stage1_plan_node(state: WorkflowRuntimeState) -> WorkflowRuntimeState:
    state.outline = _stage1_outline(state.topic, state.profile_context)
    osteps = state.outline.get("outline_steps") or state.outline.get("outlineSteps") or []
    if not isinstance(osteps, list) or not osteps:
        raise ValueError("outline_steps missing")
    state.step_states = [
        WorkflowStepState(idx=i, outline_step=s if isinstance(s, dict) else {"title": f"步骤{i+1}", "purpose": ""})
        for i, s in enumerate(osteps)
    ]
    state.debug_log.append({"node": "Stage1Plan", "steps_count": len(state.step_states)})
    return state


def _stage2_act_node(state: WorkflowRuntimeState, step_state: WorkflowStepState) -> WorkflowStepState:
    t0 = time.perf_counter()
    step_state.draft = build_step_draft_serial(
        state.topic,
        state.profile_context,
        step_state.outline_step,
        state.user_attrs,
        runtime_state=state,
    )
    step_state.key_timings = list(step_state.draft.get("_key_timings") or [])
    step_state.step_obj = normalize_step_draft(step_state.draft, state.topic, state.user_attrs)
    step_state.stage2_ms = int((time.perf_counter() - t0) * 1000)
    state.debug_log.append({"node": "Stage2Act", "step_index": step_state.idx, "title": step_state.step_obj.get("title")})
    return step_state


def _stage3_review_node(state: WorkflowRuntimeState, step_state: WorkflowStepState) -> WorkflowStepState:
    t0 = time.perf_counter()
    while step_state.review_round < state.max_review_rounds:
        r0 = time.perf_counter()
        step_state.review_round += 1
        ok, issues, repaired = review_and_repair_keys(
            step_state.step_obj,
            state.topic,
            state.profile_context,
            state.user_attrs,
            runtime_state=state,
        )
        step_state.ok = ok
        step_state.missing_keys = issues
        step_state.step_obj = repaired
        step_state.repair_log.append({
            "round": step_state.review_round,
            "issues": issues,
            "ok": ok,
            "elapsed_ms": int((time.perf_counter() - r0) * 1000),
        })
        state.debug_log.append({
            "node": "Stage3Review",
            "step_index": step_state.idx,
            "round": step_state.review_round,
            "issues": issues,
            "ok": ok,
        })
        if ok:
            break
    step_state.stage3_ms = int((time.perf_counter() - t0) * 1000)
    return step_state


def generate_workflow_chain(topic: str, profile_context: str = "", user_attrs: Optional[List[Dict[str, Any]]] = None, allow_fallback: bool = True) -> Dict[str, Any]:
    user_attrs = user_attrs or []
    try:
        t0_total = time.perf_counter()
        t0_stage1 = time.perf_counter()
        state = WorkflowRuntimeState(topic=topic, profile_context=profile_context, user_attrs=user_attrs, max_review_rounds=3)
        state = _stage1_plan_node(state)
        stage1_ms = int((time.perf_counter() - t0_stage1) * 1000)

        expanded: List[Dict[str, Any]] = []
        for ss in state.step_states:
            ss = _stage2_act_node(state, ss)
            ss = _stage3_review_node(state, ss)
            if not ss.ok and not allow_fallback:
                raise ValueError(f"step_review_failed_after_3_rounds: {ss.step_obj.get('title', f'step_{ss.idx + 1}')}")
            expanded.append(ss.step_obj)
        plan = {
            "mode": "workflow_chain",
            "response": state.outline.get("response") or "已生成任务链草案。",
            "steps": expanded,
            "estimatedDuration": state.outline.get("estimatedDuration") or "—",
            "meta": {
                "fallback": False,
                "debug": {
                    "max_review_rounds": state.max_review_rounds,
                    "stage_time_breakdown": {
                        "stage1_ms": stage1_ms,
                        "stage2_total_ms": sum(ss.stage2_ms for ss in state.step_states),
                        "stage3_total_ms": sum(ss.stage3_ms for ss in state.step_states),
                        "total_ms": int((time.perf_counter() - t0_total) * 1000),
                    },
                    "llm_call_count": state.metrics.get("llm_call_count", 0),
                    "cache_hit_count": state.metrics.get("cache_hit_count", 0),
                    "batch_call_count": state.metrics.get("batch_call_count", 0),
                    "steps": [
                        {
                            "idx": ss.idx,
                            "title": ss.step_obj.get("title"),
                            "review_round": ss.review_round,
                            "missing_keys": ss.missing_keys,
                            "repair_log": ss.repair_log,
                            "stage2_ms": ss.stage2_ms,
                            "stage3_ms": ss.stage3_ms,
                            "key_timings": ss.key_timings,
                        }
                        for ss in state.step_states
                    ],
                    "graph_log": state.debug_log,
                },
            },
        }
        return _sanitize_generated_plan(plan, topic, user_attrs)
    except Exception as e:
        if not allow_fallback:
            raise
        plan = {
            "mode": "workflow_chain",
            "response": f"生成失败，已返回兜底草案：{str(e)}",
            "steps": [
                {"title": "核对目标与交付物", "description": f"围绕「{topic}」明确交付物、边界与完成条件，并列出执行清单。"},
                {"title": "执行并记录证据", "description": "按清单执行关键动作，记录关键步骤与结果，输出阶段成果并附证据。"},
            ],
            "estimatedDuration": "—",
            "meta": {"fallback": True, "reason": str(e)},
        }
        return _sanitize_generated_plan(plan, topic, user_attrs)


def generate_single_task(topic: str, profile_context: str = "", user_attrs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    user_attrs = user_attrs or []
    prompt = PromptTemplate.from_template("""
你是虚空系统任务顾问。为简单目标生成一个单任务 JSON（可直接 /api/tasks 入库）。
目标：{topic}
用户画像上下文：{profile_context}

输出字段：task_name/description/related_attrs/estimated_time/reward_coins/priority/attribute_points/completion_type/completion_criteria/task_type
completion_criteria 必须包含 criteria/deliverables/checks/pass_threshold/evidence，且 deliverables/checks/evidence 不得为空数组。
若 related_attrs 为空，则 attribute_points 必须为 0。
""")
    task = _invoke_llm_for_json(prompt, {"topic": topic, "profile_context": profile_context}, temperature=0.6, json_mode=False)
    # 补齐与生成 attribute_plan（含属性名）
    task_name = str(task.get("task_name", "")).strip() or topic[:28] or "新任务"
    desc = str(task.get("description", "")).strip() or "请按目标完成并提交可验证证明。"
    related = task.get("related_attrs")
    related = related if isinstance(related, dict) else {}
    if not related:
        intents = _attribute_intent_plan({"title": task_name, "description": desc}, user_attrs)
        related = _attribute_resolution(intents, user_attrs)
    try:
        attr_points = int(float(task.get("attribute_points", 0) or 0))
    except Exception:
        attr_points = 0
    if related and attr_points <= 0:
        attr_points = 6
    if attr_points > 0 and not related:
        attr_points = 0
    cc = task.get("completion_criteria")
    cc = cc if isinstance(cc, dict) else {}
    defaults = _default_step_completion_criteria(topic[:36], task_name, desc)
    for k in ("criteria", "deliverables", "checks", "pass_threshold", "evidence"):
        if cc.get(k) in (None, "", []) or k not in cc:
            cc[k] = defaults[k]
    attr_points, attr_plan, related_attrs_detail = _attribute_distribution(related, attr_points, user_attrs)
    cc["attribute_plan"] = attr_plan
    task.update({
        "task_name": task_name,
        "description": desc,
        "related_attrs": related,
        "attribute_points": max(0, attr_points),
        "completion_criteria": cc,
        "related_attrs_detail": related_attrs_detail,
    })
    return task


# ==================== Backward-compatible safe invoke ====================
def safe_invoke_chain(chain: Runnable, topic: str, profile_context: str = "", user_attrs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    保持旧调用口：尝试 structured chain，失败后 json chain，最终兜底草案。
    """
    user_attrs = user_attrs or []
    try:
        result = chain.invoke({"topic": topic, "profile_context": profile_context})
        if hasattr(result, "dict"):
            result = result.dict()
        if isinstance(result, dict):
            result.setdefault("meta", {"fallback": False})
            result.setdefault("mode", "workflow_chain")
            return _sanitize_generated_plan(result, topic, user_attrs)
        raise ValueError("chain output not dict")
    except Exception as e:
        # 尝试 json chain
        try:
            json_chain = load_json_task_chain()
            result = json_chain.invoke({"topic": topic, "profile_context": profile_context})
            if isinstance(result, dict):
                result.setdefault("meta", {"fallback": True, "reason": str(e)})
                result.setdefault("mode", "workflow_chain")
                return _sanitize_generated_plan(result, topic, user_attrs)
        except Exception:
            pass
        # 最终兜底
        return generate_workflow_chain(topic, profile_context=profile_context, user_attrs=user_attrs, allow_fallback=True)


# ==================== Evaluation ====================
def evaluate_submission(task_info: Dict[str, Any], submission_info: Dict[str, Any], user_stats: Dict[str, Any]) -> Dict[str, Any]:
    model = get_chat_llm(temperature=0.3, json_mode=False)
    parser = PydanticOutputParser(pydantic_object=TaskEvaluationResult)
    prompt = PromptTemplate(
        template="""您是虚空系统的最高评判官。请根据以下信息评判用户是否完成了任务。

【任务信息】
名称: {task_name}
描述: {task_description}
评判标准: {criteria}

【用户提交内容】
证明文本: {submission}
媒体链接: {media_urls}

【当前用户属性状态】
{user_attributes}

【评判要求】
1) 结合【评判标准】打分，严厉拒绝敷衍提交。
2) feedback 要指出缺失证据或不足。
3) score 0-100，<70 必须 fail。
4) fail 时 suggested_rewards 必须全 0。
5) 输出严格 JSON。

{format_instructions}
""",
        input_variables=["task_name", "task_description", "criteria", "submission", "media_urls", "user_attributes"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | model
    attr_str = "\n".join(
        [f"- {a['attr_name']}: {a['attr_value']}/{a['max_value']}" for a in user_stats.get("attributes", [])]
    )
    invoke_payload = {
        "task_name": task_info.get("task_name", "未知任务"),
        "task_description": task_info.get("description", ""),
        "criteria": json.dumps(task_info.get("completion_criteria", {}), ensure_ascii=False),
        "submission": submission_info.get("submission", ""),
        "media_urls": ", ".join(submission_info.get("media_urls", []) or []),
        "user_attributes": attr_str,
    }
    try:
        result = chain.invoke(invoke_payload)
    except Exception as e:
        msg = str(e).lower()
        should_retry_ollama = (
            ("not found" in msg or "404" in msg)
            and str(config.LLM_PROVIDER or "").lower() == "ollama"
        )
        if not should_retry_ollama:
            raise
        fallback_model = _pick_first_available_ollama_model()
        if not fallback_model:
            raise
        logger.warning(
            "评判模型不可用，自动回退模型: %s -> %s",
            config.CHAT_MODEL,
            fallback_model,
        )
        fallback_chain = prompt | ChatOllama(
            model=fallback_model,
            base_url=config.OLLAMA_BASE_URL,
            temperature=0.3,
        )
        result = fallback_chain.invoke(invoke_payload)
    text = result.content if hasattr(result, "content") else str(result)
    js = _extract_json_object(text)
    parsed = json.loads(js)
    if isinstance(parsed, dict) and "status" in parsed:
        return parsed
    return {"status": "fail", "feedback": "评判结果解析失败", "score": 0, "suggested_rewards": {"coins": 0}}


def _pick_first_available_ollama_model() -> Optional[str]:
    try:
        base = str(config.OLLAMA_BASE_URL or "http://127.0.0.1:11434").rstrip("/")
        with urlopen(f"{base}/api/tags", timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, ValueError):
        return None
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return None
    for item in models:
        if isinstance(item, dict) and item.get("name"):
            return str(item["name"])
    return None

