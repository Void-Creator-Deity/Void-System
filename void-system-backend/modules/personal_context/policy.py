"""Explicit, user-facing rules for personal context used by AI features."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from core.personal_context_contracts import PersonalContextError


@dataclass(frozen=True)
class ContextUsePolicy:
    """One deliberate purpose and the minimum personal information it may use."""

    purpose: str
    requested_sections: Tuple[str, ...]
    profile_domains: Tuple[str, ...]
    item_budget: int
    user_explanation: str
    include_account_profile: bool = False


_POLICIES: Dict[str, ContextUsePolicy] = {
    "companion_briefing": ContextUsePolicy(
        purpose="companion_briefing",
        requested_sections=(
            "goals",
            "runs",
            "growth",
            "profile",
            "memories",
            "knowledge",
            "rewards",
        ),
        profile_domains=("working_style", "current_phase", "interests", "communication"),
        item_budget=24,
        user_explanation="用于整理你正在推进的事、当前方向和已确认的个人理解。",
    ),
    "planning_assist": ContextUsePolicy(
        purpose="planning_assist",
        requested_sections=("goals", "runs", "growth", "profile", "rewards"),
        profile_domains=("working_style", "current_phase", "interests"),
        item_budget=12,
        user_explanation="用于让规划更贴合你的当前目标、推进方式和能力方向。",
    ),
    "conversation_assist": ContextUsePolicy(
        purpose="conversation_assist",
        requested_sections=(
            "profile",
            "memories",
            "goals",
            "runs",
            "growth",
            "knowledge",
            "rewards",
        ),
        profile_domains=("working_style", "communication", "interests", "current_phase"),
        item_budget=18,
        user_explanation=(
            "用于让对话承接你已确认的偏好、正在推进的事项、成长方向和资源情况；"
            "开启资料馆权限后，只会按当前问题检索你资料馆内的相关内容。"
        ),
    ),
    "action_assist": ContextUsePolicy(
        purpose="action_assist",
        requested_sections=("runs", "goals"),
        profile_domains=(),
        item_budget=8,
        user_explanation="用于确认当前要推进的事项；不会读取个人画像或记忆。",
    ),
}


def resolve_context_policy(purpose: str) -> ContextUsePolicy:
    """Return the fixed rule for an AI use case instead of inferring it from prompts."""
    policy = _POLICIES.get(str(purpose or "").strip())
    if policy is None:
        raise PersonalContextError("Unknown AI context purpose.", "UNKNOWN_CONTEXT_PURPOSE")
    return policy


def list_context_policies() -> Tuple[ContextUsePolicy, ...]:
    return tuple(_POLICIES.values())
