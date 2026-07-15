"""HTTP checks for system status, health semantics, and response metadata."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class SystemHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "system.db"
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

    def test_root_and_healthy_dependency_return_current_version_and_request_id(self) -> None:
        root = self.client.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.json()["data"]["version"], "0.3.0")

        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        body = health.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "healthy")
        self.assertEqual(body["data"]["database"], "healthy")
        self.assertEqual(body["data"]["version"], "0.3.0")
        self.assertTrue(health.headers["X-Request-ID"])

    def test_database_failure_is_visible_to_health_check_clients(self) -> None:
        database = self.client.app.state.database
        with patch.object(database, "test_connection", side_effect=RuntimeError("offline")):
            response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error_code"], "DATABASE_UNAVAILABLE")
        self.assertEqual(body["data"]["status"], "unhealthy")
        self.assertEqual(body["data"]["database"], "unhealthy")
        self.assertTrue(response.headers["X-Request-ID"])

    def test_route_discovery_includes_business_routes_from_lazy_router_includes(self) -> None:
        response = self.client.get("/api/routes")

        self.assertEqual(response.status_code, 200)
        paths = {route["path"] for route in response.json()["data"]["routes"]}
        self.assertTrue({"/api/tasks", "/api/task-chains", "/api/ai/advisor", "/api/knowledge/system/ask"}.issubset(paths))

    def test_allowed_origin_receives_cors_headers(self) -> None:
        response = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")


if __name__ == "__main__":
    unittest.main()
