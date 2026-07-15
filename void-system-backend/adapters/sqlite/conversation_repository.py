"""SQLite Adapter for user-owned conversations."""
from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from typing import Any, Callable, Dict, List, Optional
import uuid


class SQLiteConversationRepository:
    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]):
        self._connection_factory = connection_factory

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def list_groups(self, user_id: str) -> List[Dict[str, Any]]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM chat_groups WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            groups = [dict(row) for row in cursor.fetchall()]
            for group in groups:
                cursor.execute(
                    """SELECT * FROM chat_sessions
                       WHERE group_id = ? AND user_id = ?
                       ORDER BY updated_at DESC""",
                    (group["group_id"], user_id),
                )
                group["sessions"] = [dict(row) for row in cursor.fetchall()]
            return groups
        finally:
            connection.close()

    def create_group(self, user_id: str, name: str) -> str:
        group_id = str(uuid.uuid4())
        connection = self._connection_factory()
        try:
            connection.execute(
                "INSERT INTO chat_groups (group_id, user_id, group_name) VALUES (?, ?, ?)",
                (group_id, user_id, name),
            )
            connection.commit()
            return group_id
        finally:
            connection.close()

    def update_group(self, user_id: str, group_id: str, name: str) -> bool:
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                "UPDATE chat_groups SET group_name = ? WHERE group_id = ? AND user_id = ?",
                (name, group_id, user_id),
            )
            connection.commit()
            return cursor.rowcount > 0
        finally:
            connection.close()

    def delete_group(self, user_id: str, group_id: str) -> bool:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT session_id FROM chat_sessions WHERE group_id = ? AND user_id = ?",
                (group_id, user_id),
            )
            session_ids = [row[0] for row in cursor.fetchall()]
            if session_ids:
                placeholders = ",".join("?" for _ in session_ids)
                cursor.execute(
                    f"DELETE FROM chat_messages WHERE user_id = ? AND session_id IN ({placeholders})",
                    (user_id, *session_ids),
                )
                cursor.execute(
                    f"DELETE FROM user_session_files WHERE user_id = ? AND session_id IN ({placeholders})",
                    (user_id, *session_ids),
                )
            cursor.execute(
                "DELETE FROM chat_sessions WHERE group_id = ? AND user_id = ?",
                (group_id, user_id),
            )
            cursor.execute(
                "DELETE FROM chat_groups WHERE group_id = ? AND user_id = ?",
                (group_id, user_id),
            )
            deleted = cursor.rowcount > 0
            connection.commit()
            return deleted
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create_session(
        self,
        user_id: str,
        group_id: str,
        name: str,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        connection = self._connection_factory()
        try:
            owner = connection.execute(
                "SELECT 1 FROM chat_groups WHERE group_id = ? AND user_id = ?",
                (group_id, user_id),
            ).fetchone()
            if owner is None:
                return None
            value = session_id or str(uuid.uuid4())
            now = self._now()
            connection.execute(
                """INSERT INTO chat_sessions
                   (session_id, group_id, user_id, session_name, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (value, group_id, user_id, name, now, now),
            )
            connection.commit()
            return value
        except sqlite3.IntegrityError:
            connection.rollback()
            return None
        finally:
            connection.close()

    def update_session(
        self,
        user_id: str,
        session_id: str,
        name: Optional[str],
        group_id: Optional[str],
    ) -> bool:
        connection = self._connection_factory()
        try:
            if group_id is not None:
                target = connection.execute(
                    "SELECT 1 FROM chat_groups WHERE group_id = ? AND user_id = ?",
                    (group_id, user_id),
                ).fetchone()
                if target is None:
                    return False
            fields: List[str] = []
            params: List[Any] = []
            if name is not None:
                fields.append("session_name = ?")
                params.append(name)
            if group_id is not None:
                fields.append("group_id = ?")
                params.append(group_id)
            if not fields:
                return False
            fields.append("updated_at = ?")
            params.extend([self._now(), session_id, user_id])
            cursor = connection.execute(
                f"UPDATE chat_sessions SET {', '.join(fields)} WHERE session_id = ? AND user_id = ?",
                params,
            )
            connection.commit()
            return cursor.rowcount > 0
        finally:
            connection.close()

    def delete_session(self, user_id: str, session_id: str) -> bool:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            exists = cursor.execute(
                "SELECT 1 FROM chat_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if exists is None:
                return False
            cursor.execute(
                "DELETE FROM chat_messages WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            )
            cursor.execute(
                "DELETE FROM user_session_files WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            )
            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            )
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def duplicate_session(self, user_id: str, session_id: str) -> Optional[str]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            source = cursor.execute(
                "SELECT * FROM chat_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if source is None:
                return None
            new_session_id = str(uuid.uuid4())
            now = self._now()
            cursor.execute(
                """INSERT INTO chat_sessions
                   (session_id, group_id, user_id, session_name, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (new_session_id, source["group_id"], user_id, f'{source["session_name"]} (副本)', now, now),
            )
            cursor.execute(
                """SELECT * FROM chat_messages
                   WHERE session_id = ? AND user_id = ? ORDER BY created_at ASC""",
                (session_id, user_id),
            )
            messages = cursor.fetchall()
            id_map = {row["message_id"]: str(uuid.uuid4()) for row in messages}
            for row in messages:
                cursor.execute(
                    """INSERT INTO chat_messages
                       (message_id, session_id, user_id, role, content, tokens, reply_to_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        id_map[row["message_id"]],
                        new_session_id,
                        user_id,
                        row["role"],
                        row["content"],
                        row["tokens"],
                        id_map.get(row["reply_to_id"]),
                        row["created_at"],
                    ),
                )
            connection.commit()
            return new_session_id
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_messages(self, user_id: str, session_id: str, limit: int) -> Optional[List[Dict[str, Any]]]:
        connection = self._connection_factory()
        try:
            owner = connection.execute(
                "SELECT 1 FROM chat_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if owner is None:
                return None
            cursor = connection.execute(
                """SELECT m.*, r.content AS reply_content
                   FROM chat_messages m
                   LEFT JOIN chat_messages r
                     ON m.reply_to_id = r.message_id
                    AND r.session_id = m.session_id
                    AND r.user_id = m.user_id
                   WHERE m.session_id = ? AND m.user_id = ?
                   ORDER BY m.created_at ASC LIMIT ?""",
                (session_id, user_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        tokens: int,
        reply_to_id: Optional[str],
    ) -> Optional[str]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            owner = cursor.execute(
                "SELECT 1 FROM chat_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if owner is None:
                return None
            if reply_to_id is not None:
                reply = cursor.execute(
                    """SELECT 1 FROM chat_messages
                       WHERE message_id = ? AND session_id = ? AND user_id = ?""",
                    (reply_to_id, session_id, user_id),
                ).fetchone()
                if reply is None:
                    return None
            message_id = str(uuid.uuid4())
            now = self._now()
            cursor.execute(
                """INSERT INTO chat_messages
                   (message_id, session_id, user_id, role, content, tokens, reply_to_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (message_id, session_id, user_id, role, content, tokens, reply_to_id, now),
            )
            cursor.execute(
                """UPDATE chat_sessions SET updated_at = ?
                   WHERE session_id = ? AND user_id = ?""",
                (now, session_id, user_id),
            )
            connection.commit()
            return message_id
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def clear_messages(self, user_id: str, session_id: str) -> bool:
        connection = self._connection_factory()
        try:
            owner = connection.execute(
                "SELECT 1 FROM chat_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if owner is None:
                return False
            connection.execute(
                "DELETE FROM chat_messages WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            )
            connection.commit()
            return True
        finally:
            connection.close()
