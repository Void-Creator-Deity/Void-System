"""Ordered SQLite migration tests."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from adapters.sqlite.migrations import Migration, SchemaCompatibilityError, run_migrations
from database import Database


class SQLiteMigrationTests(unittest.TestCase):
    def test_fresh_database_uses_only_canonical_task_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "schema.db")
            connection = database.get_connection()
            try:
                versions = [
                    (row[0], row[1])
                    for row in connection.execute(
                        "SELECT version, name FROM schema_migrations ORDER BY version"
                    ).fetchall()
                ]
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                reward_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(task_reward_settlements)"
                    ).fetchall()
                }
                step_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(task_steps)"
                    ).fetchall()
                }
            finally:
                connection.close()

        self.assertEqual(versions[-1], (38, "retire_legacy_user_experience"))
        self.assertTrue({"task_goals", "task_runs", "task_steps", "task_events", "plan_generation_jobs", "plan_drafts", "knowledge_document_versions", "knowledge_ingestion_jobs", "user_library_entries"} <= tables)
        self.assertFalse({"coins", "experience", "user_resources", "purchase_history"} & tables)
        self.assertIn("growth_point_ledger", tables)
        self.assertFalse({"tasks", "task_chains", "task_categories", "legacy_task_execution_links", "legacy_chain_execution_links"} & tables)
        self.assertTrue({"run_id", "step_id", "growth_points"} <= reward_columns)
        self.assertFalse({"coins", "experience", "attribute_increments"} & reward_columns)
        self.assertIn("reward_spec", step_columns)
        self.assertNotIn("task_id", reward_columns)

    def test_fresh_database_rejects_non_object_step_reward_specifications(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "reward-spec.db")
            connection = database.get_connection()
            try:
                connection.execute(
                    "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
                    ("user", "reward-user", "unused"),
                )
                connection.execute(
                    """INSERT INTO task_goals
                       (goal_id, user_id, title, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    ("goal", "user", "Goal", "2026-07-20T00:00:00", "2026-07-20T00:00:00"),
                )
                connection.execute(
                    """INSERT INTO task_runs
                       (run_id, goal_id, user_id, title, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    ("run", "goal", "user", "Run", "2026-07-20T00:00:00", "2026-07-20T00:00:00"),
                )
                connection.execute(
                    """INSERT INTO task_steps
                       (step_id, run_id, user_id, client_key, title, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    ("step", "run", "user", "step", "Step", "2026-07-20T00:00:00", "2026-07-20T00:00:00"),
                )
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "UPDATE task_steps SET reward_spec = ? WHERE step_id = 'step'",
                        (json.dumps(["not", "an", "object"]),),
                    )
            finally:
                connection.close()

    def test_migration_36_removes_marketplace_tables_from_an_upgraded_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "retired-marketplace.db"
            database = Database(path)
            connection = database.get_connection()
            try:
                connection.execute("CREATE TABLE user_resources (resource_id TEXT PRIMARY KEY)")
                connection.execute("CREATE TABLE purchase_history (purchase_id TEXT PRIMARY KEY)")
                connection.execute("DELETE FROM schema_migrations WHERE version IN (36, 37, 38)")
                connection.commit()
            finally:
                connection.close()

            upgraded = Database(path)
            connection = upgraded.get_connection()
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                migrations = connection.execute(
                    "SELECT version, name FROM schema_migrations WHERE version IN (36, 37, 38) ORDER BY version"
                ).fetchall()
            finally:
                connection.close()

        self.assertNotIn("user_resources", tables)
        self.assertNotIn("purchase_history", tables)
        self.assertEqual(
            [(row[0], row[1]) for row in migrations],
            [
                (36, "canonical_step_rewards_and_retire_marketplace"),
                (37, "canonical_growth_point_ledger"),
                (38, "retire_legacy_user_experience"),
            ],
        )

    def test_migration_37_renames_legacy_coin_ledger_without_losing_points(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "legacy-growth-ledger.db"
            database = Database(path)
            connection = database.get_connection()
            try:
                connection.execute(
                    "INSERT INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
                    ("owner", "owner", "unused"),
                )
                connection.execute("ALTER TABLE growth_point_ledger RENAME TO coins")
                connection.execute(
                    """INSERT INTO coins (record_id, user_id, amount, type, source, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    ("legacy-point", "owner", 23, "earned", "task_complete", "2026-07-20T00:00:00"),
                )
                connection.execute("DELETE FROM schema_migrations WHERE version IN (37, 38)")
                connection.commit()
            finally:
                connection.close()

            upgraded = Database(path)
            connection = upgraded.get_connection()
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                record = connection.execute(
                    """SELECT amount, source FROM growth_point_ledger
                       WHERE record_id = 'legacy-point'"""
                ).fetchone()
                settlement_columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(task_reward_settlements)"
                    ).fetchall()
                }
            finally:
                connection.close()

        self.assertIn("growth_point_ledger", tables)
        self.assertNotIn("coins", tables)
        self.assertNotIn("experience", tables)
        self.assertEqual(tuple(record), (23, "task_complete"))
        self.assertEqual(
            settlement_columns,
            {"settlement_id", "user_id", "run_id", "step_id", "growth_points", "source", "created_at"},
        )

    def test_migration_38_removes_legacy_user_experience_column(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "legacy-user-experience.db"
            database = Database(path)
            connection = database.get_connection()
            try:
                connection.execute("ALTER TABLE users ADD COLUMN experience INTEGER NOT NULL DEFAULT 0")
                connection.execute("DELETE FROM schema_migrations WHERE version = 38")
                connection.commit()
            finally:
                connection.close()

            upgraded = Database(path)
            connection = upgraded.get_connection()
            try:
                user_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()
                }
            finally:
                connection.close()

        self.assertNotIn("experience", user_columns)

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


    def test_task_object_json_migration_repairs_double_encoded_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "double-encoded.db"
            database = Database(path)
            connection = database.get_connection()
            try:
                connection.execute("DROP TRIGGER validate_task_steps_object_json_insert")
                connection.execute("DROP TRIGGER validate_task_steps_object_json_update")
                connection.execute("DELETE FROM schema_migrations WHERE version IN (24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38)")
                connection.execute("INSERT INTO users (user_id, username) VALUES ('owner', 'owner')")
                connection.execute(
                    """INSERT INTO task_goals
                       (goal_id, user_id, title, description, desired_outcome, status,
                        priority, metadata, created_at, updated_at)
                       VALUES ('goal', 'owner', 'Goal', '', '', 'active', 'medium', '{}', 'now', 'now')"""
                )
                connection.execute(
                    """INSERT INTO task_runs
                       (run_id, goal_id, user_id, title, objective, mode, status,
                        metadata, created_at, updated_at)
                       VALUES ('run', 'goal', 'owner', 'Run', '', 'manual', 'queued', '{}', 'now', 'now')"""
                )
                connection.execute(
                    """INSERT INTO task_steps
                       (step_id, run_id, user_id, client_key, title, description, kind,
                        status, position, completion_criteria, input_data, output_data,
                        created_at, updated_at)
                       VALUES ('step', 'run', 'owner', 'step-1', 'Step', '', 'manual',
                               'pending', 0, ?, '{}', '{}', 'now', 'now')""",
                    (json.dumps(json.dumps({"criteria": "Done"})),),
                )
                connection.commit()
            finally:
                connection.close()

            upgraded = Database(path)
            connection = upgraded.get_connection()
            try:
                repaired = connection.execute(
                    "SELECT completion_criteria FROM task_steps WHERE step_id = 'step'"
                ).fetchone()[0]
                recorded = connection.execute(
                    "SELECT version, name FROM schema_migrations WHERE version IN (24, 25, 26, 27) ORDER BY version"
                ).fetchall()
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "UPDATE task_steps SET completion_criteria = ? WHERE step_id = 'step'",
                        (json.dumps(["not", "an", "object"]),),
                    )
            finally:
                connection.close()

        self.assertEqual(json.loads(repaired), {"criteria": "Done"})
        self.assertEqual(
            [(row[0], row[1]) for row in recorded],
            [
                (24, "normalize_task_object_json"),
                (25, "enforce_task_object_json_contract"),
                (26, "durable_plan_generation_leases"),
                (27, "persist_plan_drafts"),
            ],
        )

    def test_migration_history_with_a_gap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "gap.db"

            def connect() -> sqlite3.Connection:
                return sqlite3.connect(path)

            migrations = [
                Migration(1, "one", lambda connection: None),
                Migration(2, "two", lambda connection: None),
                Migration(3, "three", lambda connection: None),
            ]
            run_migrations(connect, migrations)
            connection = connect()
            try:
                connection.execute("DELETE FROM schema_migrations WHERE version = 2")
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(SchemaCompatibilityError):
                run_migrations(connect, migrations)

    def test_unknown_or_renamed_migration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "drift.db"

            def connect() -> sqlite3.Connection:
                return sqlite3.connect(path)

            migrations = [Migration(1, "known", lambda connection: None)]
            run_migrations(connect, migrations)
            connection = connect()
            try:
                connection.execute(
                    "UPDATE schema_migrations SET name = 'manually-renamed' WHERE version = 1"
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(SchemaCompatibilityError):
                run_migrations(connect, migrations)

            connection = connect()
            try:
                connection.execute(
                    "UPDATE schema_migrations SET name = 'known' WHERE version = 1"
                )
                connection.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (2, 'future', 'now')"
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(SchemaCompatibilityError):
                run_migrations(connect, migrations)

    def test_database_health_rejects_schema_drift_after_startup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Database(Path(temp_dir) / "health.db")
            connection = database.get_connection()
            try:
                connection.execute(
                    "UPDATE schema_migrations SET name = 'tampered' WHERE version = 27"
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(SchemaCompatibilityError):
                database.test_connection()

    def test_legacy_task_table_without_mapping_table_aborts_retirement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "partial-legacy.db"
            database = Database(path)
            connection = database.get_connection()
            try:
                connection.execute("DELETE FROM schema_migrations WHERE version IN (23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38)")
                connection.execute(
                    "CREATE TABLE tasks (task_id TEXT PRIMARY KEY, user_id TEXT NOT NULL)"
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaisesRegex(
                RuntimeError, "legacy_task_execution_links is missing"
            ):
                Database(path)


if __name__ == "__main__":
    unittest.main()
