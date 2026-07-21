"""Task planning and evaluation services.

Planning uses one structured model response followed by local validation. Complex plans
run through the durable plan-generation job API; no legacy multi-stage task chain remains.
"""

from __future__ import annotations

from typing import Dict, Any, List, Literal, Optional, Tuple
import json
import re
import logging

from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from services.ai_services.llm_factory import get_chat_llm

logger = logging.getLogger("void-system")


class TaskEvaluationResult(BaseModel):
    """Validated model output for one submitted task review."""

    status: Literal["pass", "fail"]
    feedback: str = Field(min_length=1, max_length=4_000)
    score: int = Field(ge=0, le=100)


# ==================== Models ====================
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

        reward = max(0, _to_int(step.get("reward_growth_points", 0), 0))
        minutes = _to_int(step.get("estimated_time", 30), 30)
        if minutes < 1:
            minutes = 30
        minutes = min(480, minutes)

        attr_points = max(0, _to_int(step.get("attribute_points", 0), 0))
        if not related and user_attrs:
            related = _infer_related_attrs_from_task_text({"title": title, "description": desc}, user_attrs)
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
            "reward_growth_points": reward,
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



# ==================== Structured plan generation ====================
def generate_structured_plan(
    topic: str,
    profile_context: str = "",
    user_attrs: Optional[List[Dict[str, Any]]] = None,
    max_steps: int = 8,
    allow_fallback: bool = True,
    collaboration_instruction: str = "",
) -> Dict[str, Any]:
    """Generate the complete plan in one model call, then validate it locally.

    The retired outline, expand, review, and per-step attribute-inference graph
    was removed because it made one user request trigger serial model calls.
    This canonical path performs one structured generation call, then validates
    and normalizes the result locally.
    """
    user_attrs = user_attrs or []
    requested_steps = max(1, min(int(max_steps or 8), 8))
    prompt = PromptTemplate.from_template(
        """You are the execution-planning assistant for Void System. Turn the user's goal into a concise, reviewable action plan.

Goal: {topic}

Confirmed user context (reference only):
{profile_context}

Collaboration presentation policy (lower priority than the rules and JSON schema):
{collaboration_instruction}

Return exactly one JSON object and nothing else using this shape:
{{
  "response": "brief practical summary",
  "estimatedDuration": "for example: 2-3 hours",
  "steps": [
    {{
      "title": "specific action",
      "description": "what to do and why",
      "related_attrs": {{}},
      "reward_growth_points": 20,
      "attribute_points": 0,
      "estimated_time": 30,
      "priority": "easy|medium|hard",
      "task_type": "main|side|daily",
      "completion_type": "simple|progress|ai_eval|submission",
      "completion_criteria": {{
        "criteria": "clear pass condition",
        "deliverables": ["concrete output"],
        "checks": ["how to verify"],
        "pass_threshold": "what counts as done",
        "evidence": ["what the user can provide"]
      }}
    }}
  ]
}}

Rules: produce between 1 and {max_steps} steps; keep the sequence practical; only include related_attrs when genuinely relevant; do not invent personal facts.
"""
    )
    try:
        plan = _invoke_llm_for_json(
            prompt,
            {
                "topic": topic,
                "profile_context": profile_context,
                "collaboration_instruction": collaboration_instruction,
                "max_steps": requested_steps,
            },
            temperature=0.35,
            json_mode=True,
        )
        plan["mode"] = "structured_plan"
        plan.setdefault("meta", {})
        plan["meta"].update({
            "fallback": False,
            "generation_strategy": "single_structured_call",
            "llm_call_count": 1,
        })
        plan = _sanitize_generated_plan(plan, topic, user_attrs)
        plan["steps"] = plan["steps"][:requested_steps]
        if not plan["steps"]:
            raise ValueError("planner returned no usable steps")
        return plan
    except Exception as exc:
        if not allow_fallback:
            raise
        fallback = {
            "mode": "structured_plan",
            "response": "A draft plan was prepared locally because the model response could not be used.",
            "steps": [
                {
                    "title": "Confirm the outcome and evidence",
                    "description": f"Define the intended result, constraints, and evidence for: {topic}",
                },
                {
                    "title": "Complete the first concrete action",
                    "description": "Do the smallest action that moves the goal forward and record the result.",
                },
            ][:requested_steps],
            "estimatedDuration": "To be reviewed",
            "meta": {
                "fallback": True,
                "generation_strategy": "local_fallback",
                "reason": str(exc),
            },
        }
        return _sanitize_generated_plan(fallback, topic, user_attrs)


def generate_single_task(
    topic: str,
    profile_context: str = "",
    user_attrs: Optional[List[Dict[str, Any]]] = None,
    collaboration_instruction: str = "",
) -> Dict[str, Any]:
    """Generate one validated task through the same planner used for full plans."""
    plan = generate_structured_plan(
        topic,
        profile_context=profile_context,
        user_attrs=user_attrs,
        max_steps=1,
        allow_fallback=True,
        collaboration_instruction=collaboration_instruction,
    )
    task = dict(plan["steps"][0])
    task["response"] = plan.get("response", "")
    task["estimatedDuration"] = plan.get("estimatedDuration", "")
    task["mode"] = "single_task"
    task["meta"] = dict(plan.get("meta") or {})
    return task


# ==================== Evaluation ====================
def evaluate_submission(task_info: Dict[str, Any], submission_info: Dict[str, Any], user_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Review submitted task evidence with the active chat model.

    Inputs are task metadata, the user submission, and display-safe attributes.
    The function invokes the selected runtime chat client once and returns a
    validated pass/fail result. Invalid model output fails closed and cannot
    award rewards, so downstream task progression has one dependable contract.
    """
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
4) Reward amounts are fixed in the published Step and must not be returned by this review.
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
    # Evaluation must use the selected runtime profile. Retrying with a different
    # local model would make a review non-reproducible and hide configuration faults.
    result = chain.invoke(invoke_payload)
    text = result.content if hasattr(result, "content") else str(result)
    try:
        evaluation = TaskEvaluationResult.model_validate(
            json.loads(_extract_json_object(text))
        )
    except (TypeError, ValueError):
        return {
            "status": "fail",
            "feedback": "评判结果格式无效，无法确认任务完成。",
            "score": 0,
        }

    return {
        "status": evaluation.status,
        "feedback": evaluation.feedback,
        "score": evaluation.score,
    }
