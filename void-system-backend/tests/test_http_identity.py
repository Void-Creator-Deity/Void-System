"""End-to-end HTTP checks for account lifecycle and error contracts."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class IdentityHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "identity.db"
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

    def register(self, email: str = "member@example.com", username: str = "member") -> dict:
        response = self.client.post(
            "/api/auth/register",
            json={"email": email, "username": username, "password": "secure-password-2026"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        return body["data"]

    def login(self, identifier: str = "member@example.com", password: str = "secure-password-2026") -> dict:
        response = self.client.post(
            "/api/auth/login",
            json={"identifier": identifier, "password": password},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        return body["data"]

    @staticmethod
    def authorization(access_token: str) -> dict:
        return {"Authorization": f"Bearer {access_token}"}

    def test_register_login_refresh_rotation_and_logout(self) -> None:
        self.register()
        tokens = self.login()

        profile = self.client.get("/api/user/profile", headers=self.authorization(tokens["access_token"]))
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["data"]["email"], "member@example.com")

        wrong_kind = self.client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
        self.assertEqual(wrong_kind.status_code, 401)
        self.assertEqual(wrong_kind.json()["error_code"], "TOKEN_INVALID")
        self.assertIsNotNone(wrong_kind.json()["request_id"])

        refreshed = self.client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        self.assertEqual(refreshed.status_code, 200)
        refreshed_tokens = refreshed.json()["data"]
        self.assertNotEqual(refreshed_tokens["refresh_token"], tokens["refresh_token"])

        logout = self.client.post(
            "/api/auth/logout",
            headers=self.authorization(refreshed_tokens["access_token"]),
            json={"all_sessions": False},
        )
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(logout.json()["data"]["revoked_sessions"], 1)

        rejected = self.client.get(
            "/api/user/profile", headers=self.authorization(refreshed_tokens["access_token"])
        )
        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(rejected.json()["error_code"], "INVALID_CREDENTIALS")

        new_tokens = self.login()
        rotated = self.client.post("/api/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
        self.assertEqual(rotated.status_code, 200)
        rotated_tokens = rotated.json()["data"]

        replay = self.client.post("/api/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
        self.assertEqual(replay.status_code, 401)
        self.assertEqual(replay.json()["error_code"], "TOKEN_INVALID")

        replay_rejected = self.client.get(
            "/api/user/profile", headers=self.authorization(rotated_tokens["access_token"])
        )
        self.assertEqual(replay_rejected.status_code, 401)
        self.assertEqual(replay_rejected.json()["error_code"], "INVALID_CREDENTIALS")

    def test_profile_contract_and_password_rotation_revoke_sessions(self) -> None:
        self.register()
        tokens = self.login()

        invalid_profile = self.client.put(
            "/api/user/profile",
            headers=self.authorization(tokens["access_token"]),
            json={},
        )
        self.assertEqual(invalid_profile.status_code, 422)
        self.assertEqual(invalid_profile.json()["error_code"], "VALIDATION_ERROR")
        self.assertIn("errors", invalid_profile.json()["details"])

        updated = self.client.put(
            "/api/user/profile",
            headers=self.authorization(tokens["access_token"]),
            json={"username": "updated-member", "learning_goal": "建立稳定的学习节奏"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["username"], "updated-member")

        changed = self.client.put(
            "/api/user/password",
            headers=self.authorization(tokens["access_token"]),
            json={"current_password": "secure-password-2026", "new_password": "new-secure-password-2026"},
        )
        self.assertEqual(changed.status_code, 200)

        revoked = self.client.get("/api/user/profile", headers=self.authorization(tokens["access_token"]))
        self.assertEqual(revoked.status_code, 401)

        old_login = self.client.post(
            "/api/auth/login",
            json={"identifier": "updated-member", "password": "secure-password-2026"},
        )
        self.assertEqual(old_login.status_code, 401)

        new_tokens = self.login("updated-member", "new-secure-password-2026")
        self.assertTrue(new_tokens["access_token"])

    def test_identity_rejects_query_parameter_profile_updates(self) -> None:
        self.register()
        tokens = self.login()
        response = self.client.put(
            "/api/user/profile",
            params={"username": "not-a-body"},
            headers=self.authorization(tokens["access_token"]),
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_code"], "VALIDATION_ERROR")


if __name__ == "__main__":
    unittest.main()
