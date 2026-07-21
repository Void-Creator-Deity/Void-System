"""SQLite adapter for account identity and device session persistence."""
from __future__ import annotations

from datetime import datetime
import sqlite3
from typing import Any, Callable, Dict, Optional


class SQLiteIdentityRepository:
    """Concentrates identity SQL and keeps ownership/session invariants local."""

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]):
        self._connection_factory = connection_factory

    @staticmethod
    def _next_user_id(cursor: sqlite3.Cursor) -> str:
        cursor.execute("SELECT user_id FROM users WHERE user_id != '0000'")
        numeric_ids = [int(row[0]) for row in cursor.fetchall() if str(row[0]).isdigit()]
        return "1001" if not numeric_ids else str(max(numeric_ids) + 1)

    def add_user(
        self,
        username: str,
        email: Optional[str],
        password_hash: Optional[str],
    ) -> Optional[str]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            user_id = self._next_user_id(cursor)
            try:
                cursor.execute(
                    "INSERT INTO users (user_id, username, email, password_hash) VALUES (?, ?, ?, ?)",
                    (user_id, username, email, password_hash),
                )
            except sqlite3.IntegrityError:
                connection.rollback()
                return None
            connection.commit()
            return user_id
        finally:
            connection.close()

    def _get_user(self, column: str, value: str) -> Optional[Dict[str, Any]]:
        connection = self._connection_factory()
        try:
            row = connection.execute(
                f"SELECT * FROM users WHERE {column} = ?", (value,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self._get_user("username", username)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self._get_user("email", email)

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._get_user("user_id", user_id)

    def update_last_login(self, user_id: str) -> None:
        connection = self._connection_factory()
        try:
            connection.execute(
                "UPDATE users SET last_login = ? WHERE user_id = ?",
                (datetime.now().isoformat(), user_id),
            )
            connection.commit()
        finally:
            connection.close()

    def update_user_profile(
        self,
        user_id: str,
        *,
        email: Optional[str],
        username: Optional[str],
        learning_goal: Optional[str],
        specialization: Optional[str],
    ) -> bool:
        updates: list[str] = []
        parameters: list[Any] = []
        for column, value in (
            ("email", email),
            ("username", username),
            ("learning_goal", learning_goal),
            ("specialization", specialization),
        ):
            if value is not None:
                updates.append(f"{column} = ?")
                parameters.append(value)
        if not updates:
            return False
        connection = self._connection_factory()
        try:
            parameters.append(user_id)
            cursor = connection.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", parameters
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def update_user_password(self, user_id: str, password_hash: str, changed_at: str) -> bool:
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                """UPDATE users
                   SET password_hash = ?, password_changed_at = ?, token_version = token_version + 1
                   WHERE user_id = ?""",
                (password_hash, changed_at, user_id),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM task_steps WHERE user_id = ?", (user_id,))
            total_tasks = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM task_steps WHERE user_id = ? AND status = 'completed'", (user_id,)
            )
            completed_tasks = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM task_steps WHERE user_id = ? AND status IN ('ready', 'running', 'waiting_approval')", (user_id,)
            )
            in_progress_tasks = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM growth_point_ledger WHERE user_id = ?",
                (user_id,),
            )
            growth_points = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM user_documents WHERE user_id = ?", (user_id,))
            total_documents = cursor.fetchone()[0]
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks else 0,
                "growth_points": growth_points,
                "total_documents": total_documents,
            }
        finally:
            connection.close()

    def create_auth_session(
        self,
        session_id: str,
        user_id: str,
        refresh_token_hash: str,
        expires_at: str,
        created_at: str,
        user_agent: Optional[str],
        ip_address: Optional[str],
    ) -> None:
        connection = self._connection_factory()
        try:
            connection.execute(
                """INSERT INTO auth_sessions
                   (session_id, user_id, refresh_token_hash, expires_at, created_at, user_agent, ip_address)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, user_id, refresh_token_hash, expires_at, created_at, user_agent, ip_address),
            )
            connection.commit()
        finally:
            connection.close()

    def get_auth_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        connection = self._connection_factory()
        try:
            row = connection.execute(
                "SELECT * FROM auth_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def rotate_auth_session(
        self,
        session_id: str,
        user_id: str,
        expected_refresh_hash: str,
        replacement_refresh_hash: str,
        expires_at: str,
        used_at: str,
    ) -> bool:
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                """UPDATE auth_sessions
                   SET refresh_token_hash = ?, expires_at = ?, last_used_at = ?
                   WHERE session_id = ? AND user_id = ?
                     AND refresh_token_hash = ? AND revoked_at IS NULL AND expires_at > ?""",
                (replacement_refresh_hash, expires_at, used_at, session_id, user_id, expected_refresh_hash, used_at),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def revoke_auth_session(self, session_id: str, user_id: str, revoked_at: str) -> bool:
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                """UPDATE auth_sessions SET revoked_at = ?
                   WHERE session_id = ? AND user_id = ? AND revoked_at IS NULL""",
                (revoked_at, session_id, user_id),
            )
            connection.commit()
            return cursor.rowcount == 1
        finally:
            connection.close()

    def revoke_all_auth_sessions(self, user_id: str, revoked_at: str) -> int:
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                "UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (revoked_at, user_id),
            )
            connection.commit()
            return cursor.rowcount
        finally:
            connection.close()
