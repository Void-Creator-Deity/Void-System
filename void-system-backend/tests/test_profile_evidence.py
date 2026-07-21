"""Tests for consented, metadata-only profile signal collection."""
from __future__ import annotations

import unittest
from typing import Any, Dict, Mapping

from modules.personal_context.evidence import ProfileEvidenceCollector
from modules.personal_context.observation_adapters import TaskReviewObservationAdapter


class TaskSummaryStub:
    def __init__(self, summary: Mapping[str, Any]) -> None:
        self.summary = summary

    def summarize_profile_behavior(self, owner_id: str) -> Mapping[str, Any]:
        return self.summary


class ProfileWriterStub:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, Any]] = {}

    def upsert_signal(self, owner_id: str, values: Dict[str, Any]) -> Dict[str, Any]:
        self.records[values["source_ref"]] = dict(values)
        return {"signal_id": values["source_ref"], **values}


class ProfileEvidenceCollectorTests(unittest.TestCase):
    def test_collects_idempotent_chinese_aggregate_signals(self) -> None:
        tasks = TaskSummaryStub({
            "goal_count": 4,
            "run_count": 7,
            "completed_run_count": 5,
            "cancelled_run_count": 1,
            "assisted_run_count": 2,
            "step_count": 12,
            "finished_step_count": 9,
            "review_count": 3,
            "review_with_next_action_count": 2,
            "pause_count": 1,
            "resume_count": 2,
            "retry_count": 1,
            "goal_plan_refinement_count": 3,
            "refined_goal_count": 2,
            "signal_ranges": {},
        })
        profile = ProfileWriterStub()

        first = ProfileEvidenceCollector(tasks, profile).collect("owner-1")  # type: ignore[arg-type]
        second = ProfileEvidenceCollector(tasks, profile).collect("owner-1")  # type: ignore[arg-type]

        self.assertEqual(len(first), 6)
        self.assertEqual(len(second), 6)
        self.assertEqual(len(profile.records), 6)
        self.assertIn("已记录", profile.records["task_reviews:v1"]["summary"])
        self.assertEqual(profile.records["task_runs:v1"]["attributes"]["assisted_run_count"], 2)
        self.assertNotIn("title", str(profile.records).lower())
        self.assertNotIn("notes", str(profile.records).lower())

    def test_reads_legacy_agent_count_only_when_canonical_count_is_absent(self) -> None:
        tasks = TaskSummaryStub({
            "goal_count": 3,
            "run_count": 3,
            "completed_run_count": 2,
            "cancelled_run_count": 0,
            "agent_run_count": 1,
            "step_count": 0,
            "finished_step_count": 0,
            "review_count": 0,
            "review_with_next_action_count": 0,
            "pause_count": 0,
            "resume_count": 0,
            "retry_count": 0,
            "goal_plan_refinement_count": 0,
            "refined_goal_count": 0,
            "signal_ranges": {},
        })
        profile = ProfileWriterStub()

        ProfileEvidenceCollector(tasks, profile).collect("owner-1")  # type: ignore[arg-type]

        self.assertEqual(profile.records["task_runs:v1"]["attributes"]["assisted_run_count"], 1)

    def test_sparse_history_does_not_create_weak_signals(self) -> None:
        tasks = TaskSummaryStub({
            "goal_count": 1,
            "run_count": 1,
            "completed_run_count": 1,
            "cancelled_run_count": 0,
            "assisted_run_count": 0,
            "step_count": 1,
            "finished_step_count": 1,
            "review_count": 0,
            "review_with_next_action_count": 0,
            "pause_count": 0,
            "resume_count": 0,
            "retry_count": 0,
            "goal_plan_refinement_count": 0,
            "refined_goal_count": 0,
            "signal_ranges": {},
        })
        profile = ProfileWriterStub()
        self.assertEqual([], ProfileEvidenceCollector(tasks, profile).collect("owner-1"))  # type: ignore[arg-type]
        self.assertEqual(profile.records, {})

    def test_task_review_adapter_never_copies_task_or_review_text_into_signal(self) -> None:
        profile = ProfileWriterStub()
        adapter = TaskReviewObservationAdapter(profile)  # type: ignore[arg-type]
        adapter.record_run_review(
            "owner-1",
            {"run_id": "run-1", "title": "Very private project title", "goal_id": "goal-1"},
            {
                "outcome": "Sensitive review outcome",
                "rating": 5,
                "notes": "Private reflection notes",
                "next_action": "Private follow up",
                "updated_at": "2026-07-19T10:00:00+00:00",
            },
        )
        record = profile.records["run:run-1:review"]
        self.assertEqual(record["summary"], "一次任务复盘已记录。")
        self.assertNotIn("Very private", str(record))
        self.assertNotIn("Sensitive review", str(record))
        self.assertNotIn("Private reflection", str(record))
        self.assertNotIn("Private follow", str(record))
        self.assertEqual(record["attributes"]["rating"], 5)
        self.assertTrue(record["attributes"]["has_notes"])
        self.assertTrue(record["attributes"]["has_next_action"])


if __name__ == "__main__":
    unittest.main()
