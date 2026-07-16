"""Tests for the local-only administrator recovery tool."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from database import Database
from middleware.auth import get_password_hash, verify_password
from tools.reset_local_admin import reset_local_admin


class ResetLocalAdminToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "admin-reset.db"
        self.database = Database(self.database_path)

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def _create_admin(self) -> None:
        created = self.database.ensure_default_admin(
            "legacy-admin",
            "legacy-admin@example.com",
            get_password_hash("Legacy-password-2025!"),
        )
        self.assertTrue(created)

    def test_reset_updates_identity_password_and_revokes_sessions(self) -> None:
        self._create_admin()
        self.database.create_auth_session(
            "session-1",
            "0000",
            "refresh-digest",
            "2099-01-01T00:00:00+00:00",
            "2026-07-16T00:00:00+00:00",
        )

        result = reset_local_admin(
            self.database_path,
            "New-admin-password-2026!",
            username="admin",
            email="ADMIN@void-system.com",
        )

        self.assertEqual(
            result,
            {"user_id": "0000", "username": "admin", "email": "admin@void-system.com"},
        )
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            user = connection.execute(
                "SELECT * FROM users WHERE user_id = '0000'"
            ).fetchone()
            session = connection.execute(
                "SELECT * FROM auth_sessions WHERE session_id = 'session-1'"
            ).fetchone()
        finally:
            connection.close()

        self.assertEqual(user["username"], "admin")
        self.assertEqual(user["email"], "admin@void-system.com")
        self.assertEqual(user["role"], "admin")
        self.assertEqual(user["is_active"], 1)
        self.assertEqual(user["token_version"], 1)
        self.assertIsNotNone(user["password_changed_at"])
        self.assertTrue(verify_password("New-admin-password-2026!", user["password_hash"]))
        self.assertIsNotNone(session["revoked_at"])

    def test_identifier_cannot_promote_a_regular_user(self) -> None:
        self.database.add_user(
            "regular-user",
            "regular@example.com",
            get_password_hash("Regular-password-2026!"),
        )

        with self.assertRaisesRegex(LookupError, "没有找到管理员账号"):
            reset_local_admin(
                self.database_path,
                "New-admin-password-2026!",
                identifier="regular-user",
            )

    def test_reset_rejects_duplicate_identity(self) -> None:
        self._create_admin()
        self.database.add_user(
            "reserved-name",
            "reserved@example.com",
            get_password_hash("Regular-password-2026!"),
        )

        with self.assertRaisesRegex(ValueError, "已被其他账号使用"):
            reset_local_admin(
                self.database_path,
                "New-admin-password-2026!",
                username="reserved-name",
                email="admin@void-system.com",
            )

        with self.assertRaisesRegex(ValueError, "已被其他账号使用"):
            reset_local_admin(
                self.database_path,
                "New-admin-password-2026!",
                username="admin",
                email="reserved@example.com",
            )

    def test_reset_requires_an_existing_admin(self) -> None:
        with self.assertRaisesRegex(LookupError, "没有找到管理员账号"):
            reset_local_admin(self.database_path, "New-admin-password-2026!")

    def test_reset_rejects_missing_database_and_invalid_password(self) -> None:
        with self.assertRaisesRegex(ValueError, "至少包含 8 个字符"):
            reset_local_admin(self.database_path, "short")

        with self.assertRaisesRegex(FileNotFoundError, "数据库不存在"):
            reset_local_admin(
                Path(self.temp_dir.name) / "missing.db",
                "New-admin-password-2026!",
            )


if __name__ == "__main__":
    unittest.main()
