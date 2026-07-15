"""Regression tests for application-scoped legacy planning adapters."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from adapters.legacy.planning_adapters import LegacyAdvisorPlanningEngine, LegacyTaskEvaluationEngine
from core.planning_contracts import EvaluationRequest, PlanRequest
from core.runtime_settings import RuntimeSettings
from services.ai_services.llm_factory import active_runtime_settings


class PlanningRuntimeSettingsTests(unittest.TestCase):
    def test_planning_adapter_scopes_its_runtime_settings(self) -> None:
        settings = RuntimeSettings(CHAT_MODEL="test-model")
        captured = []

        def fake_generate_single_task(*args, **kwargs):
            captured.append(active_runtime_settings())
            return {"title": "Focus", "description": "Do one thing", "response": "Ready"}

        advisor_chain = types.ModuleType("services.ai_services.advisor_chain")
        advisor_chain.generate_single_task = fake_generate_single_task
        advisor_chain.generate_workflow_chain = lambda *args, **kwargs: {"steps": []}
        with patch.dict(sys.modules, {"services.ai_services.advisor_chain": advisor_chain}):
            result = LegacyAdvisorPlanningEngine(settings).plan(
                PlanRequest(topic="Focus", mode="single_task")
            )

        self.assertEqual(result.tasks[0].title, "Focus")
        self.assertIs(captured[0], settings)

    def test_evaluation_adapter_scopes_its_runtime_settings(self) -> None:
        settings = RuntimeSettings(CHAT_MODEL="test-model")
        captured = []

        def fake_evaluate_submission(*args, **kwargs):
            captured.append(active_runtime_settings())
            return {"status": "pass", "feedback": "Good", "score": 90}

        advisor_chain = types.ModuleType("services.ai_services.advisor_chain")
        advisor_chain.evaluate_submission = fake_evaluate_submission
        with patch.dict(sys.modules, {"services.ai_services.advisor_chain": advisor_chain}):
            result = LegacyTaskEvaluationEngine(settings).evaluate(
                EvaluationRequest(task={}, submission={}, user_stats={})
            )

        self.assertEqual(result.status, "pass")
        self.assertIs(captured[0], settings)


if __name__ == "__main__":
    unittest.main()
