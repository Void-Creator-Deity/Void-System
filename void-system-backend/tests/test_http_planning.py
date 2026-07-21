"""HTTP checks for Planning Engine transport behavior."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from adapters.sqlite.plan_draft_repository import SQLitePlanDraftRepository
from adapters.sqlite.plan_generation_repository import SQLitePlanGenerationRepository

from api.http.application import ApplicationOptions, create_app
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
                    enable_plan_generation_worker=False,
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

    def test_retired_synchronous_planning_routes_are_not_public(self) -> None:
        """Keep all first-party planning on durable jobs and persisted review drafts."""
        for route in ("/api/plans", "/api/ai/advisor"):
            response = self.client.post(route, headers=self.headers, json={"topic": "Retired route check"})
            self.assertEqual(response.status_code, 404, route)

        paths = self.client.get("/api/openapi.json").json()["paths"]
        self.assertIn("/api/plan-generations", paths)
        self.assertIn("/api/plan-drafts", paths)
        self.assertNotIn("/api/plans", paths)
        self.assertNotIn("/api/ai/advisor", paths)

    def test_durable_plan_generation_can_be_read_after_submission(self) -> None:
        created = self.client.post(
                "/api/plan-generations",
                json={"topic": "Make the job recoverable", "execution_mode": "assisted", "max_steps": 8},
                headers=self.headers,
            )

        self.assertEqual(created.status_code, 202)
        job = created.json()["data"]
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["stage"], "queued")
        self.assertEqual(job["progress"], 0)
        self.assertIsNone(job["result"])

        loaded = self.client.get(f"/api/plan-generations/{job['generation_id']}", headers=self.headers)
        self.assertEqual(loaded.status_code, 200)
        loaded_job = loaded.json()["data"]
        self.assertEqual(loaded_job["generation_id"], job["generation_id"])
        self.assertIn(loaded_job["status"], {"queued", "ready"})
        if loaded_job["status"] == "ready":
            self.assertEqual(loaded_job["result"]["goal"]["title"], "Make the job recoverable")

    def test_generation_history_is_owner_scoped_and_restorable(self) -> None:
        created = self.client.post(
            "/api/plan-generations",
            json={"topic": "Restore this plan after refresh", "execution_mode": "assisted", "max_steps": 4},
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 202)
        job = created.json()["data"]

        listed = self.client.get("/api/plan-generations", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        items = listed.json()["data"]["items"]
        restored = next(item for item in items if item["generation_id"] == job["generation_id"])
        self.assertEqual(restored["topic"], "Restore this plan after refresh")
        self.assertEqual(restored["status"], "queued")
        self.assertNotIn("lease_token", restored)


    def test_plan_draft_http_edit_and_idempotent_publish(self) -> None:
        """Exercise the first-party draft contract from persisted generation through publication."""
        database = self.client.app.state.database
        connection = database.get_connection()
        try:
            owner_id = connection.execute(
                "SELECT user_id FROM users WHERE username = ?", ("admin",)
            ).fetchone()["user_id"]
        finally:
            connection.close()
        generation = SQLitePlanGenerationRepository(database.get_connection).create(
            owner_id,
            {"topic": "Publish a saved plan", "execution_mode": "assisted", "max_steps": 2, "advisor_prefs": {}},
        )
        payload = {
            "goal": {
                "title": "发布保存的方案",
                "description": "验证端到端草稿发布。",
                "desired_outcome": "可恢复且幂等的发布",
                "priority": "high",
            },
            "run": {
                "title": "开始方案",
                "objective": "发布为正在推进的行动",
                "mode": "assisted",
                "steps": [
                    {
                        "client_key": "first",
                        "title": "完成第一步",
                        "description": "先完成可执行起点。",
                        "kind": "manual",
                        "max_attempts": 1,
                        "completion_criteria": {},
                        "input_data": {},
                        "depends_on": [],
                    }
                ],
            },
            "summary": "这是服务器持久化的方案。",
            "estimated_duration": "30 分钟",
            "meta": {"needs_review": True},
        }
        draft = SQLitePlanDraftRepository(database.get_connection).create_from_generation(
            owner_id, generation["generation_id"], payload
        )

        listed = self.client.get("/api/plan-drafts", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertIn(draft["draft_id"], [item["draft_id"] for item in listed.json()["data"]["items"]])
        loaded = self.client.get(f"/api/plan-drafts/{draft['draft_id']}", headers=self.headers)
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["data"]["version"], 1)

        payload["goal"]["title"] = "发布已保存的方案"
        saved = self.client.patch(
            f"/api/plan-drafts/{draft['draft_id']}",
            json={"payload": payload, "expected_version": 1},
            headers=self.headers,
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["data"]["version"], 2)
        published = self.client.post(
            f"/api/plan-drafts/{draft['draft_id']}/publish",
            json={"idempotency_key": "http-retry-key"},
            headers=self.headers,
        )
        self.assertEqual(published.status_code, 200)
        snapshot = published.json()["data"]
        self.assertEqual(snapshot["status"], "published")
        self.assertTrue(snapshot["published_goal_id"])
        self.assertTrue(snapshot["published_run_id"])
        retry = self.client.post(
            f"/api/plan-drafts/{draft['draft_id']}/publish",
            json={"idempotency_key": "http-retry-key"},
            headers=self.headers,
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["data"]["published_run_id"], snapshot["published_run_id"])

if __name__ == "__main__":
    unittest.main()
