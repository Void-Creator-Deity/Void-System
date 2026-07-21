"""HTTP checks for completed administrator analytics read models."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app
from core.runtime_settings import RuntimeSettings


class AdminAnalyticsHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "analytics.db"
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

    def test_all_administrator_analytics_endpoints_return_empty_safe_read_models(self) -> None:
        expected_keys = {
            "/api/admin/visualization/overview": {
                "user_stats", "task_stats", "attribute_stats", "growth_point_stats", "document_stats"
            },
            "/api/admin/visualization/users": {
                "registration_trend", "activity_stats", "level_distribution", "period_days"
            },
            "/api/admin/visualization/tasks": {
                "status_distribution", "completion_trend", "category_stats", "duration_stats", "period_days"
            },
            "/api/admin/visualization/attributes": {
                "type_distribution", "value_distribution", "popular_attributes"
            },
            "/api/admin/visualization/growth": {
                "activity_trend", "points_distribution", "health_metrics", "period_days"
            },
        }
        for endpoint, keys in expected_keys.items():
            response = self.client.get(endpoint, headers=self.headers)
            self.assertEqual(response.status_code, 200, endpoint)
            body = response.json()
            self.assertTrue(body["success"], endpoint)
            self.assertTrue(keys.issubset(body["data"]), endpoint)

    def test_regular_member_is_still_denied_administrator_analytics(self) -> None:
        registered = self.client.post(
            "/api/auth/register",
            json={
                "email": "member@example.com",
                "username": "member",
                "password": "secure-password-2026",
            },
        )
        self.assertEqual(registered.status_code, 200)
        login = self.client.post(
            "/api/auth/login",
            json={"identifier": "member", "password": "secure-password-2026"},
        )
        member_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

        response = self.client.get("/api/admin/visualization/overview", headers=member_headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error_code"], "PERMISSION_DENIED")


if __name__ == "__main__":
    unittest.main()
