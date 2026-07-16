"""Ordered SQLite migration tests."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from adapters.sqlite.migrations import Migration, run_migrations
from database import Database


class SQLiteMigrationTests(unittest.TestCase):
    def test_database_records_current_schema_versions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "schema.db")
            connection = database.get_connection()
            try:
                versions = connection.execute(
                    "SELECT version, name FROM schema_migrations ORDER BY version"
                ).fetchall()
                user_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()
                }
                indexes = {
                    row[1] for row in connection.execute("PRAGMA index_list(chat_messages)").fetchall()
                }
                task_chain_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(task_chains)").fetchall()
                }
                knowledge_tables = {
                    row[0] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                user_document_columns = {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(user_documents)"
                    ).fetchall()
                }
                task_goal_columns = {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(task_goals)"
                    ).fetchall()
                }
                task_goal_indexes = {
                    (row[1], row[2]) for row in connection.execute(
                        "PRAGMA index_list(task_goals)"
                    ).fetchall()
                }
                context_audit_columns = {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(context_access_audit)"
                    ).fetchall()
                }
                profile_observation_indexes = {
                    row[1] for row in connection.execute(
                        "PRAGMA index_list(profile_observations)"
                    ).fetchall()
                }
                personal_memory_columns = {
                    row[1] for row in connection.execute(
                        "PRAGMA table_info(personal_memories)"
                    ).fetchall()
                }
                personal_memory_indexes = {
                    row[1] for row in connection.execute(
                        "PRAGMA index_list(personal_memories)"
                    ).fetchall()
                }
            finally:
                connection.close()
            self.assertEqual(
                [(row[0], row[1]) for row in versions],
                [
                    (1, "initial_schema"),
                    (2, "runtime_columns_and_indexes"),
                    (3, "reward_marketplace_integrity"),
                    (4, "task_workspace_generation_state"),
                    (5, "knowledge_engine_lifecycle"),
                    (6, "identity_security_sessions"),
                    (7, "knowledge_document_retention"),
                    (8, "goal_run_step_task_execution"),
                    (9, "agent_run_leases"),
                    (10, "legacy_task_execution_projection"),
                    (11, "canonical_reward_settlement_links"),
                    (12, "task_triggers_and_run_commands"),
                    (13, "personal_context_and_memories"),
                    (14, "profile_cognition"),
                    (15, "goal_creation_idempotency"),
                    (16, "run_review_reflections"),
                    (17, "context_access_explanations"),
                    (18, "profile_observation_source_lookup"),
                    (19, "goal_change_history"),
                    (20, "knowledge_use_events"),
                    (21, "memory_review_lifecycle"),
                ],
            )
            self.assertIn("is_active", user_columns)
            self.assertIn("idx_chat_messages_owner_session", indexes)
            self.assertIn("generation_status", task_chain_columns)
            self.assertIn("generation_error", task_chain_columns)
            self.assertIn("knowledge_document_versions", knowledge_tables)
            self.assertIn("knowledge_ingestion_jobs", knowledge_tables)
            self.assertIn("knowledge_retrieval_traces", knowledge_tables)
            self.assertIn("knowledge_use_events", knowledge_tables)
            self.assertIn("token_version", user_columns)
            self.assertIn("auth_sessions", knowledge_tables)
            self.assertIn("is_active", user_document_columns)
            self.assertIn("archived_at", user_document_columns)
            self.assertIn("idempotency_key", task_goal_columns)
            self.assertIn(("idx_task_goals_owner_idempotency", 1), task_goal_indexes)
            self.assertTrue(
                {"source_decisions", "selected_references", "omitted_sections"}
                <= context_audit_columns
            )
            self.assertIn("idx_profile_observations_source_ref", profile_observation_indexes)
            self.assertTrue(
                {"review_status", "evidence_refs", "review_note", "reviewed_at", "expires_at"}
                <= personal_memory_columns
            )
            self.assertIn("idx_personal_memories_owner_review", personal_memory_indexes)
            self.assertIn("task_goal_changes", knowledge_tables)
            for table in (
                "task_goals",
                "task_runs",
                "task_steps",
                "task_step_dependencies",
                "task_actions",
                "task_events",
                "task_artifacts",
                "task_approvals",
                "task_run_leases",
                "legacy_task_execution_links",
                "legacy_chain_execution_links",
                "task_triggers",
                "task_trigger_firings",
                "task_run_commands",
                "task_run_reviews",
                "companion_settings",
                "personal_memories",
                "context_access_audit",
                "profile_observations",
                "profile_claims",
                "profile_overrides",
            ):
                self.assertIn(table, knowledge_tables)

    def test_applied_migration_is_not_run_twice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "idempotent.db"
            calls = []

            def connect() -> sqlite3.Connection:
                return sqlite3.connect(path)

            def apply(connection: sqlite3.Connection) -> None:
                calls.append("applied")
                connection.execute("CREATE TABLE marker (value TEXT)")

            migrations = [Migration(1, "marker", apply)]
            run_migrations(connect, migrations)
            run_migrations(connect, migrations)
            self.assertEqual(calls, ["applied"])

    def test_failed_migration_rolls_back_and_is_not_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "failure.db"

            def connect() -> sqlite3.Connection:
                return sqlite3.connect(path)

            def fail(connection: sqlite3.Connection) -> None:
                connection.execute("CREATE TABLE should_rollback (value TEXT)")
                raise RuntimeError("stop")

            with self.assertRaises(RuntimeError):
                run_migrations(connect, [Migration(1, "failing", fail)])

            connection = connect()
            try:
                recorded = connection.execute(
                    "SELECT COUNT(*) FROM schema_migrations"
                ).fetchone()[0]
                table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'should_rollback'"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(recorded, 0)
            self.assertIsNone(table)


if __name__ == "__main__":
    unittest.main()
