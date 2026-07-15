"""End-to-end HTTP checks for temporary session attachments."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.http.application import ApplicationOptions, create_app


class SessionAttachmentHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "session-files.db"
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

    def test_temporary_session_is_persisted_and_attachment_access_is_owned(self) -> None:
        owner = self.register_and_login("owner@example.com", "owner")
        other_user = self.register_and_login("other@example.com", "other")
        owner_headers = self.authorization(owner["access_token"])

        session = self.client.post("/api/session/new", headers=owner_headers)
        self.assertEqual(session.status_code, 200)
        session_id = session.json()["data"]["session_id"]

        uploaded = self.client.post(
            f"/api/session/upload-temporary?session_id={session_id}",
            headers=owner_headers,
            files={"file": ("notes.txt", b"A private attachment", "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 200)
        file_id = uploaded.json()["data"]["file_id"]

        context = self.client.get(f"/api/session/context/{session_id}", headers=owner_headers)
        self.assertEqual(context.status_code, 200)
        self.assertEqual(context.json()["data"]["file_count"], 1)

        active_sessions = self.client.get("/api/session/active", headers=owner_headers)
        self.assertEqual(active_sessions.status_code, 200)
        self.assertEqual(active_sessions.json()["data"]["session_count"], 1)
        self.assertEqual(active_sessions.json()["data"]["sessions"][0]["session_id"], session_id)

        denied = self.client.get(
            f"/api/session/context/{session_id}",
            headers=self.authorization(other_user["access_token"]),
        )
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(denied.json()["error_code"], "SESSION_NOT_FOUND")

        empty_file = self.client.post(
            f"/api/session/upload-temporary?session_id={session_id}",
            headers=owner_headers,
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        self.assertEqual(empty_file.status_code, 422)
        self.assertEqual(empty_file.json()["error_code"], "EMPTY_FILE")

        removed = self.client.delete(f"/api/session/files/{file_id}", headers=owner_headers)
        self.assertEqual(removed.status_code, 200)

        missing = self.client.get(f"/api/session/files/{file_id}", headers=owner_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error_code"], "SESSION_FILE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
