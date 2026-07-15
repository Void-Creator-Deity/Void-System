"""HTTP integration checks for conversation ownership and message lifecycle."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class ConversationHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "conversations.db"
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

    def _register_and_login(self, email: str, username: str) -> dict:
        registered = self.client.post(
            "/api/auth/register",
            json={"email": email, "username": username, "password": "secure-password-2026"},
        )
        self.assertEqual(registered.status_code, 200)
        login = self.client.post(
            "/api/auth/login",
            json={"identifier": email, "password": "secure-password-2026"},
        )
        self.assertEqual(login.status_code, 200)
        return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    def test_owner_can_manage_messages_and_other_users_cannot_read_them(self) -> None:
        owner_headers = self._register_and_login("owner@example.com", "owner")
        other_headers = self._register_and_login("other@example.com", "other")

        group = self.client.post(
            "/api/chat/groups",
            headers=owner_headers,
            json={"group_name": "Planning"},
        )
        self.assertEqual(group.status_code, 200)
        group_id = group.json()["data"]["group_id"]

        session = self.client.post(
            "/api/chat/sessions",
            headers=owner_headers,
            json={"group_id": group_id, "session_name": "Weekly review"},
        )
        self.assertEqual(session.status_code, 200)
        session_id = session.json()["data"]["session_id"]

        added = self.client.post(
            f"/api/chat/sessions/{session_id}/messages",
            headers=owner_headers,
            json={"role": "user", "content": "Review the week", "tokens": 4},
        )
        self.assertEqual(added.status_code, 200)
        self.assertTrue(added.json()["data"]["message_id"])

        messages = self.client.get(
            f"/api/chat/sessions/{session_id}/messages",
            headers=owner_headers,
        )
        self.assertEqual(messages.status_code, 200)
        self.assertEqual(len(messages.json()["data"]["messages"]), 1)
        self.assertEqual(messages.json()["data"]["messages"][0]["content"], "Review the week")

        denied = self.client.get(
            f"/api/chat/sessions/{session_id}/messages",
            headers=other_headers,
        )
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(denied.json()["error_code"], "CONVERSATION_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
