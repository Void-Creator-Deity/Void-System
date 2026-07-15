"""HTTP contract tests for Goal and Run execution."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class TaskExecutionHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.client = TestClient(
            create_app(
                ApplicationOptions(
                    database_path=str(Path(self.temp_dir.name) / "task-execution-http.db"),
                    enable_ai_routes=False,
                    enable_langserve_routes=False,
                    bootstrap_admin=False,
                )
            )
        )
        self.client.__enter__()
        registered = self.client.post(
            "/api/auth/register",
            json={
                "email": "execution@example.com",
                "username": "execution",
                "password": "secure-password-2026",
            },
        )
        self.assertEqual(registered.status_code, 200)
        logged_in = self.client.post(
            "/api/auth/login",
            json={"identifier": "execution", "password": "secure-password-2026"},
        )
        self.assertEqual(logged_in.status_code, 200)
        self.headers = {
            "Authorization": f"Bearer {logged_in.json()['data']['access_token']}"
        }

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def test_goal_run_step_and_event_contract(self) -> None:
        goal_response = self.client.post(
            "/api/goals",
            headers=self.headers,
            json={"title": "Ship a reliable release", "priority": "high"},
        )
        self.assertEqual(goal_response.status_code, 200)
        goal_id = goal_response.json()["data"]["goal"]["goal_id"]

        run_response = self.client.post(
            f"/api/goals/{goal_id}/runs",
            headers=self.headers,
            json={
                "mode": "assisted",
                "steps": [
                    {"client_key": "prepare", "title": "Prepare"},
                    {
                        "client_key": "verify",
                        "title": "Verify",
                        "kind": "review",
                        "depends_on": ["prepare"],
                    },
                ],
            },
        )
        self.assertEqual(run_response.status_code, 200)
        run = run_response.json()["data"]["run"]
        run_id = run["run_id"]

        started = self.client.post(f"/api/runs/{run_id}/start", headers=self.headers)
        self.assertEqual(started.status_code, 200)
        run = started.json()["data"]["run"]
        prepare = next(step for step in run["steps"] if step["client_key"] == "prepare")
        verify = next(step for step in run["steps"] if step["client_key"] == "verify")
        self.assertEqual(prepare["status"], "ready")
        self.assertEqual(verify["status"], "pending")

        step_started = self.client.post(
            f"/api/runs/{run_id}/steps/{prepare['step_id']}/start",
            headers=self.headers,
        )
        self.assertEqual(step_started.status_code, 200)
        completed = self.client.post(
            f"/api/runs/{run_id}/steps/{prepare['step_id']}/complete",
            headers=self.headers,
            json={
                "output_data": {"result": "prepared"},
                "artifacts": [
                    {
                        "title": "Release notes",
                        "kind": "document",
                        "uri": "memory://release-notes",
                    }
                ],
            },
        )
        self.assertEqual(completed.status_code, 200)
        run = completed.json()["data"]["run"]
        verify = next(step for step in run["steps"] if step["client_key"] == "verify")
        self.assertEqual(verify["status"], "ready")
        self.assertEqual(len(run["artifacts"]), 1)

        events = self.client.get(f"/api/runs/{run_id}/events", headers=self.headers)
        self.assertEqual(events.status_code, 200)
        event_types = [item["event_type"] for item in events.json()["data"]["events"]]
        self.assertIn("run.started", event_types)
        self.assertIn("step.completed", event_types)

    def test_invalid_dependency_is_rejected_as_domain_error(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Invalid graph"}
        ).json()["data"]["goal"]
        response = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={
                "steps": [
                    {"client_key": "only", "title": "Only", "depends_on": ["missing"]}
                ]
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "UNKNOWN_STEP_DEPENDENCY")

    def test_agent_run_lease_and_checkpoint_contract(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Research architecture"}
        ).json()["data"]["goal"]
        run = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={
                "mode": "agent",
                "steps": [{"title": "Inspect modules", "kind": "agent"}],
            },
        ).json()["data"]["run"]
        self.client.post(f"/api/runs/{run['run_id']}/start", headers=self.headers)

        claimed = self.client.post(
            f"/api/runs/{run['run_id']}/lease",
            headers=self.headers,
            json={"worker_id": "backend-worker", "lease_seconds": 60},
        )
        self.assertEqual(claimed.status_code, 200)
        token = claimed.json()["data"]["lease"]["lease_token"]

        heartbeat = self.client.post(
            f"/api/runs/{run['run_id']}/heartbeat",
            headers=self.headers,
            json={
                "lease_token": token,
                "lease_seconds": 90,
                "checkpoint_data": {"phase": "inspection", "completed": 2},
            },
        )
        self.assertEqual(heartbeat.status_code, 200)
        self.assertEqual(
            heartbeat.json()["data"]["lease"]["checkpoint_data"]["phase"],
            "inspection",
        )

        released = self.client.post(
            f"/api/runs/{run['run_id']}/lease/release",
            headers=self.headers,
            json={"lease_token": token},
        )
        self.assertEqual(released.status_code, 200)
        self.assertIsNotNone(released.json()["data"]["run"]["lease"]["released_at"])

    def test_goal_update_and_step_skip_contract(self) -> None:
        goal = self.client.post(
            "/api/goals", headers=self.headers, json={"title": "Publish handbook"}
        ).json()["data"]["goal"]
        updated = self.client.patch(
            f"/api/goals/{goal['goal_id']}",
            headers=self.headers,
            json={"title": "Publish team handbook", "priority": "high"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["goal"]["priority"], "high")

        run = self.client.post(
            f"/api/goals/{goal['goal_id']}/runs",
            headers=self.headers,
            json={"steps": [{"client_key": "draft", "title": "Draft"}]},
        ).json()["data"]["run"]
        run = self.client.post(
            f"/api/runs/{run['run_id']}/start", headers=self.headers
        ).json()["data"]["run"]
        step = run["steps"][0]
        skipped = self.client.post(
            f"/api/runs/{run['run_id']}/steps/{step['step_id']}/skip",
            headers=self.headers,
        )
        self.assertEqual(skipped.status_code, 200)
        skipped_run = skipped.json()["data"]["run"]
        self.assertEqual(skipped_run["steps"][0]["status"], "skipped")
        self.assertEqual(skipped_run["status"], "completed")

        completed_goal = self.client.patch(
            f"/api/goals/{goal['goal_id']}",
            headers=self.headers,
            json={"status": "completed"},
        )
        self.assertEqual(completed_goal.status_code, 200)
        self.assertEqual(completed_goal.json()["data"]["goal"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
