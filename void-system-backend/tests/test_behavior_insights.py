"""Unit tests for explainable first-party behavior insight candidates."""
import unittest

from modules.personal_context.behavior_insights import BehaviorInsightEngine


class _TaskHistory:
    def __init__(self, signal: dict) -> None:
        self.signal = signal

    def summarize_profile_behavior(self, user_id: str) -> dict:
        return self.signal


def _signal(**overrides: object) -> dict:
    values = {
        "run_count": 0,
        "completed_run_count": 0,
        "review_count": 0,
        "review_with_next_action_count": 0,
        "pause_count": 0,
        "resume_count": 0,
        "step_count": 0,
        "finished_step_count": 0,
        "approval_count": 0,
        "approved_approval_count": 0,
        "goal_plan_refinement_count": 0,
        "refined_goal_count": 0,
        "observation_ranges": {},
    }
    values.update(overrides)
    return values


class BehaviorInsightTests(unittest.TestCase):
    def test_empty_history_produces_no_suggestions(self) -> None:
        suggestions = BehaviorInsightEngine(_TaskHistory(_signal())).suggest("owner-1")
        self.assertEqual(suggestions, [])

    def test_review_candidate_exposes_only_aggregate_evidence_and_time_range(self) -> None:
        secret_note = "private review note must never be exposed"
        history = _TaskHistory(_signal(
            review_count=3,
            review_with_next_action_count=3,
            raw_review_notes=secret_note,
            observation_ranges={
                "reviews": {
                    "observed_from": "2026-07-01T09:00:00+00:00",
                    "observed_to": "2026-07-12T11:00:00+00:00",
                },
            },
        ))

        suggestion = BehaviorInsightEngine(history).suggest("owner-1")[0]

        self.assertEqual(suggestion["suggestion_id"], "task_behavior:follow_up_after_review")
        self.assertEqual(suggestion["first_observed_at"], "2026-07-01T09:00:00+00:00")
        self.assertEqual(suggestion["last_observed_at"], "2026-07-12T11:00:00+00:00")
        evidence = suggestion["evidence_refs"][0]["data"]
        self.assertEqual(evidence["observed_from"], suggestion["first_observed_at"])
        self.assertEqual(evidence["observed_to"], suggestion["last_observed_at"])
        self.assertNotIn(secret_note, str(suggestion))
        self.assertNotIn("raw_review_notes", str(suggestion))

    def test_pause_resume_candidate_combines_only_event_observation_ranges(self) -> None:
        history = _TaskHistory(_signal(
            pause_count=2,
            resume_count=2,
            observation_ranges={
                "pauses": {
                    "observed_from": "2026-06-02T09:00:00+00:00",
                    "observed_to": "2026-06-10T09:00:00+00:00",
                },
                "resumes": {
                    "observed_from": "2026-06-03T09:00:00+00:00",
                    "observed_to": "2026-06-11T09:00:00+00:00",
                },
            },
        ))

        suggestion = BehaviorInsightEngine(history).suggest("owner-1")[0]

        self.assertEqual(suggestion["suggestion_id"], "task_behavior:resume_after_pause")
        self.assertEqual(suggestion["first_observed_at"], "2026-06-02T09:00:00+00:00")
        self.assertEqual(suggestion["last_observed_at"], "2026-06-11T09:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
