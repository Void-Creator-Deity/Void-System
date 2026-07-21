"""Server-side companion interaction policy for durable planning."""
from __future__ import annotations

from typing import Any, Mapping

from core.planning_contracts import PlanningInteractionPolicy


_ALLOWED_TONES = {"calm", "warm", "direct"}
_ALLOWED_INITIATIVES = {"quiet", "balanced", "proactive"}


def resolve_planning_interaction_policy(settings: Mapping[str, Any]) -> PlanningInteractionPolicy:
    """Return a safe planning policy from persisted companion settings.

    Inputs: owner-scoped settings read by PersonalContext at job execution time.
    Output: a typed policy containing only tone and initiative. Calls: used by
    durable plan generation before it invokes the planning adapter. Persona text
    and all permission/execution fields are intentionally ignored.
    """
    tone = str(settings.get("tone") or "calm")
    initiative = str(settings.get("initiative") or "balanced")
    return PlanningInteractionPolicy(
        tone=tone if tone in _ALLOWED_TONES else "calm",
        initiative=initiative if initiative in _ALLOWED_INITIATIVES else "balanced",
    )
