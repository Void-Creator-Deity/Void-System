"""HTTP contract tests for the Task Workspace module adapter."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class TaskWorkspaceHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.client = TestClient(
            create_app(
                ApplicationOptions(
                    database_path=str(Path(self.temp_dir.name) / "task-workspace-http.db"),
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

    def login(self, email: str, username: str) -> dict:
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
        return {"Authorization": f"Bearer {logged_in.json()['data']['access_token']}"}

    def test_categories_and_tasks_follow_workspace_rules(self) -> None:
        headers = self.login("workspace@example.com", "workspace")
        created_category = self.client.post(
            "/api/task-categories",
            headers=headers,
            json={"category_name": "Deep work", "description": "Focused efforts"},
        )
        self.assertEqual(created_category.status_code, 200)
        category_id = created_category.json()["data"]["category_id"]

        duplicate = self.client.post(
            "/api/task-categories",
            headers=headers,
            json={"category_name": " deep WORK "},
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["error_code"], "CATEGORY_NAME_CONFLICT")

        created_task = self.client.post(
            "/api/tasks",
            headers=headers,
            json={
                "task_name": "Write module contract",
                "category_id": category_id,
                "completion_type": "progress",
                "reward_coins": 5,
            },
        )
        self.assertEqual(created_task.status_code, 200)
        task_id = created_task.json()["data"]["task_id"]

        progressed = self.client.put(
            f"/api/tasks/{task_id}/progress",
            headers=headers,
            json={"progress": 100},
        )
        self.assertEqual(progressed.status_code, 200)
        self.assertTrue(progressed.json()["data"]["reward_granted"])

        listed = self.client.get("/api/tasks", headers=headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["stats"]["total_tasks"], 1)
        self.assertEqual(listed.json()["data"]["tasks"][0]["status"], "completed")

    def test_manual_chain_creates_linked_steps_without_database_facade(self) -> None:
        headers = self.login("chains@example.com", "chains")
        created = self.client.post(
            "/api/task-chains",
            headers=headers,
            json={
                "chain_name": "Release checklist",
                "steps": [
                    {"title": "Plan", "description": "Plan the release."},
                    {"title": "Ship", "description": "Ship the release."},
                ],
            },
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["data"]["task_count"], 2)

        tasks = self.client.get("/api/tasks", headers=headers).json()["data"]["tasks"]
        by_order = sorted(tasks, key=lambda item: item["chain_order"])
        self.assertEqual(by_order[0]["prerequisites"], [])
        self.assertEqual(by_order[1]["prerequisites"], [by_order[0]["task_id"]])


if __name__ == "__main__":
    unittest.main()
