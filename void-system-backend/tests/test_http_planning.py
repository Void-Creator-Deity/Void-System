"""HTTP checks for Planning Engine transport behavior."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app
from core.planning_contracts import PlanResult, PlannedTask
from core.runtime_settings import RuntimeSettings


class PlanningHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "planning.db"
        settings = RuntimeSettings(
            BOOTSTRAP_ADMIN_ENABLED=True,
            DEFAULT_ADMIN_USERNAME="admin",
            DEFAULT_ADMIN_EMAIL="admin@example.com",
            DEFAULT_ADMIN_PASSWORD="admin-password-2026",
        )
        self.client = TestClient(
            create_app(
                ApplicationOptions(
                    database_path=str(database_path),
                    enable_ai_routes=False,
                    enable_langserve_routes=False,
                    settings=settings,
                )
            )
        )
        self.client.__enter__()
        login = self.client.post(
            "/api/auth/login",
            json={"identifier": "admin", "password": "admin-password-2026"},
        )
        self.assertEqual(login.status_code, 200)
        self.headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def test_advisor_returns_a_stable_publishable_plan_contract(self) -> None:
        plan = PlanResult(
            response="Split the goal into one focused task.",
            tasks=[
                PlannedTask(
                    title="Draft the module contract",
                    description="Write the boundary and completion criteria.",
                    estimated_time=30,
                    reward_coins=10,
                    attribute_points=0,
                    priority="medium",
                    task_type="main",
                    completion_type="simple",
                    related_attrs={},
                    completion_criteria={
                        "criteria": "A reviewed contract exists.",
                        "deliverables": ["Contract document"],
                        "checks": ["Covers the module boundary"],
                        "evidence": ["Document link"],
                    },
                    attribute_plan=[],
                )
            ],
            mode="single_task",
            estimated_duration="30 minutes",
            metadata={"fallback": False},
        )
        engine = Mock()
        engine.plan.return_value = plan

        with patch("api.http.routers.planning.get_planning_engine", return_value=engine):
            response = self.client.post(
                "/api/ai/advisor",
                json={"topic": "Define the module contract", "force_mode": "single_task"},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(
            set(data),
            {"mode", "query", "response", "estimated_duration", "tasks", "meta"},
        )
        self.assertEqual(data["mode"], "single_task")
        self.assertEqual(data["query"], "Define the module contract")
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["title"], "Draft the module contract")
        self.assertEqual(data["tasks"][0]["completion_type"], "simple")
        self.assertNotIn("steps", data)

    def test_canonical_planner_returns_goal_and_run_specification(self) -> None:
        plan = PlanResult(
            response="Prepare, implement, and review the change.",
            tasks=[
                PlannedTask(
                    title="Prepare",
                    description="Confirm the desired behavior.",
                    estimated_time=20,
                    reward_coins=0,
                    attribute_points=0,
                    priority="medium",
                    task_type="main",
                    completion_type="simple",
                    related_attrs={},
                    completion_criteria={"criteria": "Scope is confirmed."},
                    attribute_plan=[],
                ),
                PlannedTask(
                    title="Implement",
                    description="Build and verify the change.",
                    estimated_time=60,
                    reward_coins=0,
                    attribute_points=0,
                    priority="hard",
                    task_type="main",
                    completion_type="submission",
                    related_attrs={},
                    completion_criteria={"criteria": "Tests pass."},
                    attribute_plan=[],
                ),
            ],
            mode="workflow_chain",
            estimated_duration="80 minutes",
            metadata={"fallback": False},
        )
        engine = Mock()
        engine.plan.return_value = plan

        with patch("api.http.routers.planning.get_planning_engine", return_value=engine):
            response = self.client.post(
                "/api/plans",
                json={
                    "topic": "Refactor task execution",
                    "execution_mode": "agent",
                    "max_steps": 8,
                },
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(set(data), {"goal", "run", "summary", "estimated_duration", "meta"})
        self.assertEqual(data["run"]["mode"], "agent")
        self.assertEqual(data["run"]["steps"][0]["depends_on"], [])
        self.assertEqual(data["run"]["steps"][1]["depends_on"], ["step-1"])
        self.assertNotIn("single_task", str(data))
        self.assertNotIn("workflow_chain", str(data))

    def test_unexpected_planning_failure_does_not_expose_internal_error(self) -> None:
        with self.assertLogs("void-system.planning", level="ERROR") as captured:
            with patch(
                "api.http.routers.planning.get_planning_engine",
                side_effect=RuntimeError("provider token secret-value"),
            ):
                response = self.client.post(
                    "/api/ai/advisor",
                    json={"topic": "Prepare a learning plan"},
                    headers=self.headers,
                )

        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error_code"], "ADVISOR_FAILED")
        self.assertNotIn("secret-value", str(body))
        self.assertNotIn("secret-value", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
