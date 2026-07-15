"""HTTP contract tests for the Growth Profile module adapter."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class GrowthProfileHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.client = TestClient(
            create_app(
                ApplicationOptions(
                    database_path=str(Path(self.temp_dir.name) / "growth-http.db"),
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
        self.assertEqual(
            self.client.post(
                "/api/auth/register",
                json={"email": email, "username": username, "password": "secure-password-2026"},
            ).status_code,
            200,
        )
        login = self.client.post(
            "/api/auth/login",
            json={"identifier": username, "password": "secure-password-2026"},
        )
        self.assertEqual(login.status_code, 200)
        return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    def test_capabilities_are_owned_unique_and_clamped(self) -> None:
        owner_headers = self.login("growth@example.com", "growth")
        other_headers = self.login("other-growth@example.com", "other-growth")
        created = self.client.post(
            "/api/attributes",
            headers=owner_headers,
            json={"attr_name": "Focus", "max_value": 100},
        )
        self.assertEqual(created.status_code, 200)
        attr_id = created.json()["data"]["attr_id"]

        duplicate = self.client.post(
            "/api/attributes",
            headers=owner_headers,
            json={"attr_name": " focus "},
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.json()["error_code"], "ATTRIBUTE_EXISTS")

        denied = self.client.put(
            f"/api/attributes/{attr_id}",
            headers=other_headers,
            json={"attr_value": 20},
        )
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(denied.json()["error_code"], "ATTRIBUTE_NOT_FOUND")

        updated = self.client.put(
            f"/api/attributes/{attr_id}",
            headers=owner_headers,
            json={"attr_value": 80, "max_value": 40, "attr_name": "Deep focus"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["attr_value"], 40)
        self.assertEqual(updated.json()["data"]["max_value"], 40)
        self.assertEqual(updated.json()["data"]["attr_name"], "Deep focus")

        self.assertEqual(self.client.get("/api/coins/balance", headers=owner_headers).json()["data"]["balance"], 0)
        summary = self.client.get("/api/coins/stats", headers=owner_headers)
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["data"]["net_income"], 0)


if __name__ == "__main__":
    unittest.main()
