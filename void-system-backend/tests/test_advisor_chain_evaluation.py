"""Regression tests for task-evidence evaluation boundary validation."""
from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.runnables import RunnableLambda

from services.ai_services.advisor_chain import evaluate_submission


class TaskEvaluationTests(unittest.TestCase):
    """Ensure evidence review cannot choose task rewards."""

    def _evaluate(self, payload: dict | str) -> dict:
        content = payload if isinstance(payload, str) else json.dumps(payload)
        llm = RunnableLambda(lambda _: SimpleNamespace(content=content))
        with patch("services.ai_services.advisor_chain.get_chat_llm", return_value=llm):
            return evaluate_submission(
                {
                    "task_name": "Review an article",
                    "description": "Summarize the central argument.",
                    "completion_criteria": {"minimum_length": 100},
                },
                {"submission": "A short submission", "media_urls": []},
                {"attributes": []},
            )

    def test_failed_evaluation_does_not_return_model_selected_rewards(self) -> None:
        result = self._evaluate(
            {
                "status": "fail",
                "feedback": "The submitted evidence does not meet the criteria.",
                "score": 42,
            }
        )

        self.assertEqual(result["status"], "fail")
        self.assertNotIn("suggested_rewards", result)

    def test_non_json_model_output_returns_safe_failure(self) -> None:
        result = self._evaluate("I cannot provide structured output right now.")

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["score"], 0)
        self.assertNotIn("suggested_rewards", result)

    def test_invalid_contract_returns_safe_failure(self) -> None:
        result = self._evaluate(
            {
                "status": "pending",
                "feedback": "This must not be accepted.",
                "score": 130,
            }
        )

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["score"], 0)
        self.assertNotIn("suggested_rewards", result)
        self.assertTrue(result["feedback"])


if __name__ == "__main__":
    unittest.main()
