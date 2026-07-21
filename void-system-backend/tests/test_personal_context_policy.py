"""Regression checks for the user-visible companion permission contract."""

from modules.personal_context.policy import resolve_context_policy


VISIBLE_PERMISSION_SECTIONS = {
    "profile",
    "goals",
    "runs",
    "growth",
    "memories",
    "knowledge",
    "rewards",
}


def test_companion_briefing_covers_every_user_visible_permission_section():
    policy = resolve_context_policy("companion_briefing")

    assert set(policy.requested_sections) == VISIBLE_PERMISSION_SECTIONS


def test_conversation_can_use_every_enabled_personal_context_section():
    policy = resolve_context_policy("conversation_assist")

    assert set(policy.requested_sections) == VISIBLE_PERMISSION_SECTIONS


def test_planning_can_use_resource_context_when_user_enables_it():
    policy = resolve_context_policy("planning_assist")

    assert "rewards" in policy.requested_sections
