"""End-to-end HTTP checks for a user's task workflow."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class TaskWorkflowHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "task-workflow.db"
        self.client = TestClient(
            create_app(
                ApplicationOptions(
                    database_path=str(database_path),
                    enable_ai_routes=False,
                    enable_langserve_routes=False,
                    bootstrap_admin=False,
                )
            )
        )
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def register_and_login(self, email: str, username: str) -> dict:
        registered = self.client.post(
            "/api/auth/register",
            json={"email": email, "username": username, "password": "secure-password-2026"},
        )
        self.assertEqual(registered.status_code, 200)
        logged_in = self.client.post(
            "/api/auth/login",
            json={"identifier": username, "password": "secure-password-2026"},
        )
        self.assertEqual(logged_in.status_code, 200)
        return logged_in.json()["data"]

    @staticmethod
    def authorization(access_token: str) -> dict:
        return {"Authorization": f"Bearer {access_token}"}

    def test_task_lifecycle_preserves_zero_reward_and_owner_isolation(self) -> None:
        owner = self.register_and_login("owner@example.com", "owner")
        other_user = self.register_and_login("other@example.com", "other")
        owner_headers = self.authorization(owner["access_token"])

        created = self.client.post(
            "/api/tasks",
            headers=owner_headers,
            json={
                "task_name": "Read architecture notes",
                "description": "Review the system design before implementation.",
                "estimated_time": 20,
                "reward_coins": 0,
                "attribute_points": 0,
                "completion_type": "simple",
            },
        )
        self.assertEqual(created.status_code, 200)
        task_id = created.json()["data"]["task_id"]

        detail = self.client.get(f"/api/tasks/{task_id}", headers=owner_headers)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["data"]["task"]["reward_coins"], 0)

        denied = self.client.get(
            f"/api/tasks/{task_id}",
            headers=self.authorization(other_user["access_token"]),
        )
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(denied.json()["error_code"], "TASK_NOT_FOUND")

        completed = self.client.put(
            f"/api/tasks/{task_id}/status?status=completed",
            headers=owner_headers,
        )
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["data"]["status"], "completed")
        self.assertTrue(completed.json()["data"]["reward_granted"])


if __name__ == "__main__":
    unittest.main()
