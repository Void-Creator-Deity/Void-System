"""HTTP authorization checks for administrator-only configuration endpoints."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class AdministrationHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "administration.db"
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

    def test_regular_member_cannot_read_runtime_ai_configuration(self) -> None:
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
            json={"identifier": "member@example.com", "password": "secure-password-2026"},
        )
        self.assertEqual(login.status_code, 200)
        access_token = login.json()["data"]["access_token"]

        response = self.client.get(
            "/api/admin/system/ai-config",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error_code"], "PERMISSION_DENIED")
        self.assertTrue(body["request_id"])


if __name__ == "__main__":
    unittest.main()
