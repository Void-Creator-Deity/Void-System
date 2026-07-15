"""Conversation workflow ownership and lifecycle tests."""
from pathlib import Path
import tempfile
import unittest

from core.conversation_contracts import ConversationError
from database import Database
from modules.conversations.service import get_conversation_service


class ConversationWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "conversation.db")
        connection = self.database.get_connection()
        try:
            connection.executemany(
                "INSERT INTO users (user_id, username, email) VALUES (?, ?, ?)",
                [
                    ("user-a", "user-a", "a@example.com"),
                    ("user-b", "user-b", "b@example.com"),
                ],
            )
            connection.commit()
        finally:
            connection.close()
        self.service = get_conversation_service(self.database)

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def test_group_ownership_is_required_when_creating_session(self) -> None:
        group_id = self.service.create_group("user-a", "工作")
        with self.assertRaises(ConversationError) as context:
            self.service.create_session("user-b", group_id, "越权会话")
        self.assertEqual(context.exception.status_code, 404)

    def test_message_write_requires_session_ownership(self) -> None:
        group_id = self.service.create_group("user-a", "工作")
        session_id = self.service.create_session("user-a", group_id, "周计划")
        with self.assertRaises(ConversationError):
            self.service.add_message("user-b", session_id, "user", "越权消息")
        self.assertEqual(self.service.list_messages("user-a", session_id, 100), [])

    def test_duplicate_preserves_messages_and_reply_links(self) -> None:
        group_id = self.service.create_group("user-a", "工作")
        session_id = self.service.create_session("user-a", group_id, "周计划")
        first_id = self.service.add_message("user-a", session_id, "user", "第一条")
        self.service.add_message(
            "user-a", session_id, "assistant", "第二条", reply_to_id=first_id
        )
        duplicate_id = self.service.duplicate_session("user-a", session_id)
        messages = self.service.list_messages("user-a", duplicate_id, 100)
        self.assertEqual([message["content"] for message in messages], ["第一条", "第二条"])
        self.assertEqual(messages[1]["reply_content"], "第一条")

    def test_delete_group_explicitly_removes_children(self) -> None:
        group_id = self.service.create_group("user-a", "工作")
        session_id = self.service.create_session("user-a", group_id, "周计划")
        self.service.add_message("user-a", session_id, "user", "待清理")
        self.service.delete_group("user-a", group_id)

        connection = self.database.get_connection()
        try:
            session_count = connection.execute(
                "SELECT COUNT(*) FROM chat_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            message_count = connection.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(session_count, 0)
        self.assertEqual(message_count, 0)


if __name__ == "__main__":
    unittest.main()
