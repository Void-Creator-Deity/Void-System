"""Regression tests for the public layered-profile workspace."""
from modules.personal_context.layered_profile import LayeredProfileWorkspace


def test_workspace_separates_signals_patterns_hypotheses_and_confirmed_facets() -> None:
    workspace = LayeredProfileWorkspace().build(
        settings={"permissions": {"profile": True}},
        profile_view={
            "signals": [
                {
                    "signal_id": "review-1", "status": "active", "sensitivity": "private",
                    "source_ref": "task_reviews:v1", "source_type": "workspace_history_summary",
                    "observed_at": "2026-07-19T10:00:00+00:00",
                    "attributes": {"review_count": 4, "review_with_next_action_count": 3},
                },
                {
                    "signal_id": "steps-1", "status": "active", "sensitivity": "private",
                    "source_ref": "task_steps:v1", "source_type": "workspace_history_summary",
                    "observed_at": "2026-07-19T10:00:00+00:00",
                    "attributes": {"step_count": 9, "finished_step_count": 6},
                },
            ],
            "patterns": [{
                "pattern_id": "pattern-1", "status": "active",
                "label": "近期复盘会记录下一步", "detail": "在已保存的复盘中，有 3 次记录了后续行动。",
                "updated_at": "2026-07-19T10:00:00+00:00",
            }],
            "facets": [{
                "facet_id": "facet-1", "status": "active", "domain": "working_style",
                "profile_key": "reviewable-steps", "label": "偏好可检查的行动节奏",
                "value": "希望任务有明确完成条件。", "source": "user_corrected",
                "context_enabled": True, "updated_at": "2026-07-19T12:00:00+00:00",
            }],
            "hypotheses": [{
                "hypothesis_id": "hypothesis-1", "status": "pending", "domain": "working_style",
                "summary": "复盘后倾向于留下下一步行动", "rationale": "4 次复盘中有 3 次记录了后续行动。",
                "confidence": 0.76, "evidence_refs": [{"type": "profile_signal", "id": "review-1"}],
                "created_at": "2026-07-19T12:00:00+00:00",
            }],
        },
    )

    assert workspace["summary"]["established"] == 1
    assert workspace["summary"]["reviewing"] == 1
    assert workspace["facets"][0]["source"] == "你已修正"
    assert workspace["patterns"][0]["title"] == "近期复盘会记录下一步"
    assert workspace["hypotheses"][0]["evidence"][0]["label"] == "任务复盘"
    assert workspace["context_projection"]["facets"][0]["label"] == "工作方式"
    assert "review-1" not in str(workspace)
    assert "steps-1" not in str(workspace)
    assert "pattern-1" not in str(workspace)
    assert "facet-1" not in str(workspace)
    assert "observations" not in workspace


def test_workspace_excludes_sensitive_or_archived_signals() -> None:
    workspace = LayeredProfileWorkspace().build(
        settings={"permissions": {"profile": True}},
        profile_view={
            "signals": [
                {"signal_id": "sensitive", "status": "active", "sensitivity": "sensitive"},
                {"signal_id": "archived", "status": "archived", "sensitivity": "private"},
            ],
            "patterns": [], "facets": [], "hypotheses": [],
        },
    )
    assert workspace["signals"] == []
    assert workspace["patterns"] == []
    assert workspace["sources"] == []



def test_workspace_hides_historical_candidates_and_keeps_only_reviewable_suggestions() -> None:
    """Historical claims must neither render nor count as current review work."""
    workspace = LayeredProfileWorkspace().build(
        settings={"permissions": {"profile": True}},
        profile_view={
            "signals": [{
                "signal_id": "review-1", "status": "active", "sensitivity": "private",
                "source_ref": "task_reviews:v1", "source_type": "workspace_history_summary",
                "observed_at": "2026-07-19T10:00:00+00:00",
                "attributes": {"review_count": 3, "review_with_next_action_count": 2},
            }],
            "patterns": [],
            "facets": [{
                "facet_id": "corrected-1", "status": "active", "domain": "working_style",
                "profile_key": "planning-order", "label": "已修正的协作偏好",
                "value": "先给整体方案，再按阶段推进。", "source": "user_corrected",
                "context_enabled": True, "updated_at": "2026-07-19T12:00:00+00:00",
            }],
            "hypotheses": [
                {
                    "hypothesis_id": "historical-claim", "status": "pending", "domain": "working_style",
                    "summary": "Legacy profile candidate", "rationale": "An old inference contract created this row.",
                    "confidence": 0.7, "evidence_refs": [{"type": "profile_signal", "id": "review-1"}],
                    "created_at": "2026-07-19T12:00:00+00:00",
                },
                {
                    "hypothesis_id": "modern-suggestion", "status": "pending", "domain": "working_style",
                    "summary": "复盘后希望保留下一步行动", "rationale": "近期 3 次复盘中有 2 次保存了后续行动。",
                    "confidence": 0.8, "evidence_refs": [{"type": "profile_signal", "id": "review-1"}],
                    "created_at": "2026-07-19T12:00:00+00:00",
                },
            ],
        },
    )

    assert workspace["summary"]["reviewing"] == 1
    assert [item["hypothesis_id"] for item in workspace["hypotheses"]] == ["modern-suggestion"]
    assert workspace["facets"][0]["title"] == "先给整体方案，再按阶段推进。"
    assert workspace["facets"][0]["value"] == "这条协作偏好由你确认后保留，可用于后续协助。"
    public_text = str(workspace)
    for internal_term in ("historical-claim", "Legacy", "旧版", "旧候选", "profile_legacy_records"):
        assert internal_term not in public_text
    assert workspace["context_projection"]["facets"] == [{
        "label": "工作方式", "value": "先给整体方案，再按阶段推进。", "source": "你已修正",
    }]
