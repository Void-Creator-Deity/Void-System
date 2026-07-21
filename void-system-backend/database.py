"""
Void System Database Module
----------------------------
提供数据库操作接口，包括用户、属性、任务、系统币等核心功能的数据管理。
"""
import sqlite3
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import logging

from adapters.sqlite.migrations import Migration, SchemaState, inspect_schema, run_migrations

logger: logging.Logger = logging.getLogger("void-system-db")

class Database:
    def __init__(self, db_path: str = "void_system.db") -> None:
        """
        初始化数据库连接
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.schema_state = self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def test_connection(self) -> SchemaState:
        """Verify connectivity and the complete runtime/schema contract."""
        conn = self.get_connection()
        try:
            conn.execute("SELECT 1")
            return inspect_schema(conn, self._migrations(), require_latest=True)
        finally:
            conn.close()

    def close(self) -> None:
        """关闭数据库连接（如果需要）"""
        pass  # SQLite会自动管理连接

    def _migrations(self) -> tuple[Migration, ...]:
        """Return the immutable, ordered schema contract for this runtime."""
        return (
            Migration(1, "initial_schema", self._create_initial_schema),
            Migration(2, "runtime_columns_and_indexes", self._add_runtime_columns_and_indexes),
            Migration(3, "reward_marketplace_integrity", self._add_reward_marketplace_integrity),
            Migration(4, "task_workspace_generation_state", self._add_task_workspace_generation_state),
            Migration(5, "knowledge_engine_lifecycle", self._add_knowledge_engine_lifecycle),
            Migration(6, "identity_security_sessions", self._add_identity_security_sessions),
            Migration(7, "knowledge_document_retention", self._add_knowledge_document_retention),
            Migration(8, "goal_run_step_task_execution", self._add_task_execution_model),
            Migration(9, "agent_run_leases", self._add_agent_run_leases),
            Migration(10, "legacy_task_execution_projection", self._add_legacy_task_execution_projection),
            Migration(11, "canonical_reward_settlement_links", self._add_canonical_reward_settlement_links),
            Migration(12, "task_triggers_and_run_commands", self._add_task_triggers_and_run_commands),
            Migration(13, "personal_context_and_memories", self._add_personal_context_and_memories),
            Migration(14, "profile_cognition", self._add_profile_cognition),
            Migration(15, "goal_creation_idempotency", self._add_goal_creation_idempotency),
            Migration(16, "run_review_reflections", self._add_run_review_reflections),
            Migration(17, "context_access_explanations", self._add_context_access_explanations),
            Migration(18, "profile_observation_source_lookup", self._add_profile_observation_source_lookup),
            Migration(19, "goal_change_history", self._add_goal_change_history),
            Migration(20, "knowledge_use_events", self._add_knowledge_use_events),
            Migration(21, "memory_review_lifecycle", self._add_memory_review_lifecycle),
            Migration(22, "plan_generation_jobs", self._add_plan_generation_jobs),
            Migration(23, "retire_legacy_task_tables", self._retire_legacy_task_tables),
            Migration(24, "normalize_task_object_json", self._normalize_task_object_json),
            Migration(25, "enforce_task_object_json_contract", self._enforce_task_object_json_contract),
            Migration(26, "durable_plan_generation_leases", self._add_plan_generation_leases),
            Migration(27, "persist_plan_drafts", self._add_plan_drafts),
            Migration(28, "durable_knowledge_jobs", self._add_durable_knowledge_jobs),
            Migration(29, "unify_knowledge_document_catalog", self._unify_knowledge_document_catalog),
            Migration(30, "knowledge_private_content_encryption", self._add_knowledge_private_content_encryption),
            Migration(31, "user_library_entries", self._add_user_library_entries),
            Migration(32, "layered_profile_cognition", self._migrate_to_layered_profile_cognition),
            Migration(33, "retire_legacy_profile_candidates", self._retire_legacy_profile_candidates),
            Migration(34, "unify_assisted_task_execution_and_companion_persona", self._unify_assisted_task_execution_and_companion_persona),
            Migration(35, "retire_run_commands", self._retire_run_commands),
            Migration(36, "canonical_step_rewards_and_retire_marketplace", self._add_canonical_step_rewards_and_retire_marketplace),
            Migration(37, "canonical_growth_point_ledger", self._canonicalize_growth_point_ledger),
            Migration(38, "retire_legacy_user_experience", self._retire_legacy_user_experience),
        )

    def _unify_assisted_task_execution_and_companion_persona(self, conn: sqlite3.Connection) -> None:
        """Retire the non-executing agent lease model and add persisted companion identity."""
        conn.execute("UPDATE task_runs SET mode = 'assisted' WHERE mode = 'agent'")
        conn.execute(
            "UPDATE task_steps SET kind = 'manual' WHERE kind IN ('agent', 'tool', 'review')"
        )
        conn.execute("DROP TABLE IF EXISTS task_run_leases")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(companion_settings)").fetchall()}
        if "persona" not in columns:
            conn.execute(
                "ALTER TABLE companion_settings ADD COLUMN persona TEXT NOT NULL DEFAULT '{}'"
            )

    def _retire_run_commands(self, conn: sqlite3.Connection) -> None:
        """Remove the retired run-command queue from upgraded databases."""
        conn.execute("DROP TABLE IF EXISTS task_run_commands")

    def _add_canonical_step_rewards_and_retire_marketplace(self, conn: sqlite3.Connection) -> None:
        """Install fixed Step reward specifications and remove the unfulfilled marketplace.

        Inputs: the exclusive migration transaction supplied by the SQLite runner.
        Outputs: every canonical Step has a JSON reward specification; inventory and
        purchase tables no longer exist. Called once as migration 36. The runtime keeps
        historical points ledger rows, but marketplace rows are intentionally removed
        because no product entitlement or consumption contract ever existed for them.
        """
        columns = {row[1] for row in conn.execute("PRAGMA table_info(task_steps)").fetchall()}
        if "reward_spec" not in columns:
            conn.execute(
                "ALTER TABLE task_steps ADD COLUMN reward_spec TEXT NOT NULL DEFAULT '{}'"
            )
        conn.execute("DROP TRIGGER IF EXISTS validate_task_steps_object_json_insert")
        conn.execute("DROP TRIGGER IF EXISTS validate_task_steps_object_json_update")
        from adapters.sqlite.task_schema import enforce_task_object_json_contract
        enforce_task_object_json_contract(conn)
        conn.execute("DROP TABLE IF EXISTS user_resources")
        conn.execute("DROP TABLE IF EXISTS purchase_history")

    def _canonicalize_growth_point_ledger(self, conn: sqlite3.Connection) -> None:
        """Migrate legacy reward storage into one canonical growth-points ledger.

        Inputs: the exclusive SQLite migration transaction after marketplace retirement.
        Outputs: a single growth_point_ledger table and a settlement table whose only
        reward value is growth_points. Called once as migration 37 for fresh and
        upgraded stores. It preserves historical point amounts, deliberately drops the
        unconsumed experience ledger, and leaves no runtime dependency on coins.
        """
        if self._table_exists(conn, "coins") and not self._table_exists(conn, "growth_point_ledger"):
            conn.execute("ALTER TABLE coins RENAME TO growth_point_ledger")
        if not self._table_exists(conn, "growth_point_ledger"):
            conn.execute(
                """CREATE TABLE growth_point_ledger (
                    record_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    source TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )"""
            )
        conn.execute("DROP TABLE IF EXISTS experience")

        settlement_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(task_reward_settlements)").fetchall()
        }
        if settlement_columns != {
            "settlement_id", "user_id", "run_id", "step_id", "growth_points", "source", "created_at"
        }:
            conn.execute(
                """CREATE TABLE task_reward_settlements_canonical (
                    settlement_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    growth_points INTEGER NOT NULL DEFAULT 0,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, step_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )"""
            )
            legacy_growth_column = "growth_points" if "growth_points" in settlement_columns else "coins"
            conn.execute(
                f"""INSERT INTO task_reward_settlements_canonical
                   (settlement_id, user_id, run_id, step_id, growth_points, source, created_at)
                   SELECT settlement_id, user_id, run_id, step_id, {legacy_growth_column}, source, created_at
                   FROM task_reward_settlements"""
            )
            conn.execute("DROP TABLE task_reward_settlements")
            conn.execute(
                "ALTER TABLE task_reward_settlements_canonical RENAME TO task_reward_settlements"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_growth_point_ledger_user_created_at "
            "ON growth_point_ledger(user_id, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_reward_settlement_step "
            "ON task_reward_settlements(user_id, step_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_reward_settlement_run "
            "ON task_reward_settlements(user_id, run_id, created_at DESC)"
        )

    def _retire_legacy_user_experience(self, conn: sqlite3.Connection) -> None:
        """Remove the obsolete user experience column after reward canonicalization.

        Inputs: a migrated users table that may still carry the retired experience
        counter. Output: the same user records without a second growth metric.
        Called once by migration 38; all active reward records live in
        growth_point_ledger instead.
        """
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "experience" in columns:
            conn.execute("ALTER TABLE users DROP COLUMN experience")

    def init_database(self) -> SchemaState:
        """Bring the embedded store to the runtime's exact schema contract."""
        return run_migrations(self.get_connection, self._migrations())


    @staticmethod
    def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone() is not None

    def _retire_legacy_task_tables(self, conn: sqlite3.Connection) -> None:
        """Migrate every legacy task record, then remove the retired schema permanently.

        This migration intentionally fails before deleting any table when a historical task
        or reward cannot be represented by a canonical Goal, Run, and Step.
        """
        has_tasks = self._table_exists(conn, "tasks")
        has_task_links = self._table_exists(conn, "legacy_task_execution_links")
        if has_tasks:
            if not has_task_links:
                raise RuntimeError(
                    "Cannot retire legacy tasks: legacy_task_execution_links is missing"
                )
            from adapters.sqlite.legacy_migration_support.legacy_task_retirement import backfill_legacy_task_execution

            now = datetime.now().isoformat()
            backfill_legacy_task_execution(conn, now)
            unmapped_tasks = conn.execute(
                """SELECT COUNT(*) FROM tasks t
                   LEFT JOIN legacy_task_execution_links link
                     ON link.legacy_task_id = t.task_id AND link.user_id = t.user_id
                   WHERE link.legacy_task_id IS NULL"""
            ).fetchone()[0]
            if unmapped_tasks:
                raise RuntimeError(
                    f"Cannot retire legacy tasks: {unmapped_tasks} records are not mapped"
                )

        settlement_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(task_reward_settlements)").fetchall()
        }
        if "task_id" in settlement_columns:
            if has_task_links:
                conn.execute(
                    """UPDATE task_reward_settlements
                       SET run_id = COALESCE(run_id, (
                               SELECT link.run_id FROM legacy_task_execution_links link
                               WHERE link.legacy_task_id = task_reward_settlements.task_id
                                 AND link.user_id = task_reward_settlements.user_id
                           )),
                           step_id = COALESCE(step_id, (
                               SELECT link.step_id FROM legacy_task_execution_links link
                               WHERE link.legacy_task_id = task_reward_settlements.task_id
                                 AND link.user_id = task_reward_settlements.user_id
                           ))
                       WHERE run_id IS NULL OR step_id IS NULL"""
                )
            unmapped_rewards = conn.execute(
                "SELECT COUNT(*) FROM task_reward_settlements WHERE run_id IS NULL OR step_id IS NULL"
            ).fetchone()[0]
            if unmapped_rewards:
                raise RuntimeError(
                    f"Cannot retire legacy tasks: {unmapped_rewards} reward settlements are not mapped"
                )
            conn.execute(
                """CREATE TABLE task_reward_settlements_canonical (
                    settlement_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    coins INTEGER NOT NULL DEFAULT 0,
                    experience INTEGER NOT NULL DEFAULT 0,
                    attribute_increments TEXT NOT NULL DEFAULT '{}',
                    source TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, step_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                    FOREIGN KEY (step_id) REFERENCES task_steps(step_id) ON DELETE CASCADE
                )"""
            )
            conn.execute(
                """INSERT INTO task_reward_settlements_canonical
                   (settlement_id, user_id, run_id, step_id, coins, experience,
                    attribute_increments, source, created_at)
                   SELECT settlement_id, user_id, run_id, step_id, coins, experience,
                          attribute_increments, source, created_at
                   FROM task_reward_settlements"""
            )
            conn.execute("DROP TABLE task_reward_settlements")
            conn.execute("ALTER TABLE task_reward_settlements_canonical RENAME TO task_reward_settlements")

        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_task_reward_settlement_step
               ON task_reward_settlements(user_id, step_id)"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_task_reward_settlement_run
               ON task_reward_settlements(user_id, run_id, created_at DESC)"""
        )
        for table_name in (
            "legacy_task_execution_links",
            "legacy_chain_execution_links",
            "tasks",
            "task_chains",
            "task_categories",
        ):
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")

    def _normalize_task_object_json(self, conn: sqlite3.Connection) -> None:
        """Repair historical task fields that were stored as double-encoded JSON text."""
        from adapters.sqlite.object_json import encode_legacy_object

        if not self._table_exists(conn, "task_steps"):
            return
        rows = conn.execute(
            "SELECT step_id, completion_criteria FROM task_steps"
        ).fetchall()
        for row in rows:
            normalized = encode_legacy_object(
                row["completion_criteria"], legacy_text_key="criteria"
            )
            if normalized != (row["completion_criteria"] or "{}"):
                conn.execute(
                    "UPDATE task_steps SET completion_criteria = ? WHERE step_id = ?",
                    (normalized, row["step_id"]),
                )

    def _enforce_task_object_json_contract(self, conn: sqlite3.Connection) -> None:
        """Install the canonical Task Execution object-field contract."""
        from adapters.sqlite.task_schema import enforce_task_object_json_contract

        enforce_task_object_json_contract(conn)

    def _add_plan_generation_jobs(self, conn: sqlite3.Connection) -> None:
        """Persist asynchronous plan generation state and reviewable results."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_generation_jobs (
                generation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                execution_mode TEXT NOT NULL,
                max_steps INTEGER NOT NULL,
                advisor_prefs TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL,
                stage TEXT NOT NULL DEFAULT 'queued',
                progress INTEGER NOT NULL DEFAULT 0,
                result TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_plan_generation_jobs_owner_updated
                ON plan_generation_jobs(user_id, updated_at DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_plan_generation_jobs_status
                ON plan_generation_jobs(status, updated_at ASC)
            """
        )

    def _add_plan_generation_leases(self, conn: sqlite3.Connection) -> None:
        """Add reclaimable worker ownership to persisted plan-generation jobs.

        Inputs:
            conn: Migration transaction connection for a version-25 database.
        Outputs:
            A queue table capable of atomically assigning, renewing, and recovering work.
        Called by:
            `init_database` while upgrading the embedded SQLite schema.
        Side effects:
            Adds lease and cancellation columns plus indexes. Existing queued/ready/failed jobs
            keep their original user-visible state and have zero recorded attempts.
        Failure:
            SQLite migration failures abort startup and roll back this migration transaction.
        Invariants:
            Worker lease tokens never leave repository internals; generation state remains
            owner-scoped and only one non-expired worker may advance a job.
        """
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(plan_generation_jobs)").fetchall()
        }
        additions = {
            "worker_id": "TEXT",
            "lease_token": "TEXT",
            "lease_expires_at": "TEXT",
            "heartbeat_at": "TEXT",
            "attempt_count": "INTEGER NOT NULL DEFAULT 0",
            "cancel_requested": "INTEGER NOT NULL DEFAULT 0",
        }
        for column, definition in additions.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE plan_generation_jobs ADD COLUMN {column} {definition}")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_plan_generation_jobs_claim "
            "ON plan_generation_jobs(status, cancel_requested, lease_expires_at, created_at)"
        )

    def _add_plan_drafts(self, conn: sqlite3.Connection) -> None:
        """Add durable, owner-scoped Plan Drafts and link ready jobs to their review resource.

        Inputs:
            conn: Migration transaction supplied by Database.init_database.
        Outputs:
            Creates the plan_drafts table, its owner/idempotency indexes, and the nullable draft_id
            reference on historical plan_generation_jobs rows.
        Called by:
            Schema migration 27 exactly once per database.
        Side effects:
            Evolves persisted planning state without deleting historical job result payloads.
        Failure:
            SQLite aborts the surrounding migration transaction when schema creation fails.
        Invariants:
            A generation may reference one draft; publication keys are unique per user when present.
        """
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_drafts (
                draft_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                generation_id TEXT UNIQUE,
                payload TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'ready',
                version INTEGER NOT NULL DEFAULT 1,
                publication_key TEXT,
                published_goal_id TEXT,
                published_run_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (generation_id) REFERENCES plan_generation_jobs(generation_id) ON DELETE SET NULL,
                FOREIGN KEY (published_goal_id) REFERENCES task_goals(goal_id) ON DELETE SET NULL,
                FOREIGN KEY (published_run_id) REFERENCES task_runs(run_id) ON DELETE SET NULL,
                CHECK (status IN ('ready', 'published', 'discarded'))
            )
            """
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_plan_drafts_owner_updated
               ON plan_drafts(user_id, updated_at DESC)"""
        )
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_plan_drafts_owner_publication
               ON plan_drafts(user_id, publication_key) WHERE publication_key IS NOT NULL"""
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(plan_generation_jobs)").fetchall()}
        if "draft_id" not in columns:
            conn.execute("ALTER TABLE plan_generation_jobs ADD COLUMN draft_id TEXT")
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_plan_generation_jobs_draft
               ON plan_generation_jobs(draft_id)"""
        )

    def _add_memory_review_lifecycle(self, conn: sqlite3.Connection) -> None:
        """Add review, evidence, and expiry state to personal memories."""
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(personal_memories)").fetchall()
        }
        additions = {
            "review_status": "TEXT NOT NULL DEFAULT 'confirmed'",
            "evidence_refs": "TEXT NOT NULL DEFAULT '[]'",
            "review_note": "TEXT NOT NULL DEFAULT ''",
            "reviewed_at": "TEXT",
            "expires_at": "TEXT",
        }
        for column, definition in additions.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE personal_memories ADD COLUMN {column} {definition}")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_personal_memories_owner_review "
            "ON personal_memories(owner_id, review_status, status, updated_at DESC)"
        )

    def _add_knowledge_use_events(self, conn: sqlite3.Connection) -> None:
        """Store privacy-minimized knowledge-use outcomes for opt-in profile review."""
        conn.execute(
            """CREATE TABLE IF NOT EXISTS knowledge_use_events (
                   event_id TEXT PRIMARY KEY,
                   owner_id TEXT NOT NULL,
                   mode TEXT NOT NULL,
                   candidate_count INTEGER NOT NULL DEFAULT 0,
                   ranked_count INTEGER NOT NULL DEFAULT 0,
                   source_count INTEGER NOT NULL DEFAULT 0,
                   citation_count INTEGER NOT NULL DEFAULT 0,
                   answerable INTEGER NOT NULL DEFAULT 0,
                   created_at TEXT NOT NULL,
                   FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE
               )"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_knowledge_use_events_owner_created
               ON knowledge_use_events(owner_id, created_at DESC)"""
        )

    def _add_goal_change_history(self, conn: sqlite3.Connection) -> None:
        """Record non-content Goal change categories for first-party behavior summaries."""
        schema = """
            CREATE TABLE IF NOT EXISTS task_goal_changes (
                change_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                change_kind TEXT NOT NULL,
                changed_fields TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES task_goals(goal_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_task_goal_changes_owner_kind_created
                ON task_goal_changes(user_id, change_kind, created_at DESC);
        """
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)
    def _add_profile_observation_source_lookup(self, conn: sqlite3.Connection) -> None:
        """Speed idempotent evidence updates without deleting existing history."""
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_profile_observations_source_ref
               ON profile_observations(owner_id, source_type, source_ref, updated_at DESC)
               WHERE source_ref IS NOT NULL"""
        )

    def _add_run_review_reflections(self, conn: sqlite3.Connection) -> None:
        """Store user reflection separately from immutable Run evidence."""
        conn.execute(
            """CREATE TABLE IF NOT EXISTS task_run_reviews (
                   run_id TEXT NOT NULL,
                   user_id TEXT NOT NULL,
                   outcome TEXT,
                   rating INTEGER,
                   notes TEXT NOT NULL DEFAULT '',
                   next_action TEXT NOT NULL DEFAULT '',
                   created_at TEXT NOT NULL,
                   updated_at TEXT NOT NULL,
                   PRIMARY KEY (run_id, user_id),
                   FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                   FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
               )"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_task_run_reviews_owner_updated
               ON task_run_reviews(user_id, updated_at DESC)"""
        )

    def _add_goal_creation_idempotency(self, conn: sqlite3.Connection) -> None:
        """Make Goal publication retryable without creating duplicate owner records."""
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(task_goals)").fetchall()
        }
        if "idempotency_key" not in columns:
            conn.execute("ALTER TABLE task_goals ADD COLUMN idempotency_key TEXT")
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_task_goals_owner_idempotency
               ON task_goals(user_id, idempotency_key)"""
        )

    def _add_task_execution_model(self, conn: sqlite3.Connection) -> None:
        """Add durable Goal, Run, Step, Action, Event, Artifact, and Approval records."""
        schema = """
            CREATE TABLE IF NOT EXISTS task_goals (
                goal_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                desired_outcome TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                priority TEXT NOT NULL DEFAULT 'medium',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                archived_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS task_runs (
                run_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                objective TEXT NOT NULL DEFAULT '',
                mode TEXT NOT NULL DEFAULT 'manual',
                status TEXT NOT NULL DEFAULT 'queued',
                version INTEGER NOT NULL DEFAULT 1,
                idempotency_key TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                error_summary TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                paused_at TEXT,
                completed_at TEXT,
                cancelled_at TEXT,
                FOREIGN KEY (goal_id) REFERENCES task_goals(goal_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (user_id, idempotency_key)
            );

            CREATE TABLE IF NOT EXISTS task_steps (
                step_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                client_key TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                kind TEXT NOT NULL DEFAULT 'manual',
                status TEXT NOT NULL DEFAULT 'pending',
                position INTEGER NOT NULL DEFAULT 0,
                parallel_group TEXT,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 1,
                requires_approval INTEGER NOT NULL DEFAULT 0,
                progress INTEGER NOT NULL DEFAULT 0,
                completion_criteria TEXT NOT NULL DEFAULT '{}',
                input_data TEXT NOT NULL DEFAULT '{}',
                reward_spec TEXT NOT NULL DEFAULT '{}',
                output_data TEXT NOT NULL DEFAULT '{}',
                error_summary TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (run_id, client_key)
            );

            CREATE TABLE IF NOT EXISTS task_step_dependencies (
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                depends_on_step_id TEXT NOT NULL,
                PRIMARY KEY (step_id, depends_on_step_id),
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (step_id) REFERENCES task_steps(step_id) ON DELETE CASCADE,
                FOREIGN KEY (depends_on_step_id) REFERENCES task_steps(step_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS task_actions (
                action_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL,
                tool_name TEXT,
                input_data TEXT NOT NULL DEFAULT '{}',
                output_data TEXT NOT NULL DEFAULT '{}',
                error_summary TEXT,
                idempotency_key TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (step_id) REFERENCES task_steps(step_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (step_id, idempotency_key)
            );

            CREATE TABLE IF NOT EXISTS task_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_id TEXT,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (step_id) REFERENCES task_steps(step_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS task_artifacts (
                artifact_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_id TEXT,
                user_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                uri TEXT,
                content_type TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (step_id) REFERENCES task_steps(step_id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS task_approvals (
                approval_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                request_data TEXT NOT NULL DEFAULT '{}',
                decision_data TEXT NOT NULL DEFAULT '{}',
                requested_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (step_id) REFERENCES task_steps(step_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_task_goals_user_status
                ON task_goals(user_id, status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_task_runs_user_status
                ON task_runs(user_id, status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_task_runs_goal
                ON task_runs(goal_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_task_steps_run_status
                ON task_steps(run_id, status, position);
            CREATE INDEX IF NOT EXISTS idx_task_events_run_created
                ON task_events(run_id, created_at, event_id);
            CREATE INDEX IF NOT EXISTS idx_task_approvals_user_status
                ON task_approvals(user_id, status, requested_at DESC);
        """
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)

    def _add_agent_run_leases(self, conn: sqlite3.Connection) -> None:
        """Retained as a no-op so historical migration records remain compatible.

        Inputs: the migration connection. Outputs: none. Called only while a new
        database is replaying historical schema versions. The retired lease table
        must not be created because automatic task workers are no longer exposed.
        """
        return None

    def _add_legacy_task_execution_projection(self, conn: sqlite3.Connection) -> None:
        """Upgrade historical task records into the canonical execution model."""
        if not self._table_exists(conn, "tasks"):
            return
        schema = """
            CREATE TABLE IF NOT EXISTS legacy_chain_execution_links (
                legacy_chain_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                goal_id TEXT NOT NULL UNIQUE,
                run_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (legacy_chain_id) REFERENCES task_chains(chain_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES task_goals(goal_id) ON DELETE CASCADE,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS legacy_task_execution_links (
                legacy_task_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                legacy_chain_id TEXT,
                goal_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (legacy_task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
                FOREIGN KEY (legacy_chain_id) REFERENCES task_chains(chain_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES task_goals(goal_id) ON DELETE CASCADE,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (step_id) REFERENCES task_steps(step_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_legacy_task_execution_owner_run
                ON legacy_task_execution_links(user_id, run_id);
            CREATE INDEX IF NOT EXISTS idx_legacy_task_execution_chain
                ON legacy_task_execution_links(legacy_chain_id, legacy_task_id);
            CREATE INDEX IF NOT EXISTS idx_legacy_chain_execution_owner
                ON legacy_chain_execution_links(user_id, run_id);
        """
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)

        from adapters.sqlite.legacy_migration_support.legacy_task_retirement import backfill_legacy_task_execution

        backfill_legacy_task_execution(conn, datetime.now().isoformat())

    def _add_canonical_reward_settlement_links(self, conn: sqlite3.Connection) -> None:
        """Link historical reward grants to their canonical Run and Step identities."""
        columns = {
            row[1] for row in conn.execute(
                "PRAGMA table_info(task_reward_settlements)"
            ).fetchall()
        }
        if not columns or "task_id" not in columns:
            return
        if "run_id" not in columns:
            conn.execute("ALTER TABLE task_reward_settlements ADD COLUMN run_id TEXT")
        if "step_id" not in columns:
            conn.execute("ALTER TABLE task_reward_settlements ADD COLUMN step_id TEXT")
        conn.execute(
            """UPDATE task_reward_settlements
               SET run_id = (
                       SELECT link.run_id FROM legacy_task_execution_links link
                       WHERE link.legacy_task_id = task_reward_settlements.task_id
                         AND link.user_id = task_reward_settlements.user_id
                   ),
                   step_id = (
                       SELECT link.step_id FROM legacy_task_execution_links link
                       WHERE link.legacy_task_id = task_reward_settlements.task_id
                         AND link.user_id = task_reward_settlements.user_id
                   )
               WHERE run_id IS NULL OR step_id IS NULL"""
        )
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_task_reward_settlement_step
               ON task_reward_settlements(user_id, step_id) WHERE step_id IS NOT NULL"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_task_reward_settlement_run
               ON task_reward_settlements(user_id, run_id, created_at DESC)"""
        )

    def _add_task_triggers_and_run_commands(self, conn: sqlite3.Connection) -> None:
        """Add portable Trigger-to-Run automation and durable steering commands."""
        schema = """
            CREATE TABLE IF NOT EXISTS task_triggers (
                trigger_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, goal_id TEXT NOT NULL,
                name TEXT NOT NULL, trigger_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
                configuration TEXT NOT NULL DEFAULT '{}', run_template TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_fired_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES task_goals(goal_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS task_trigger_firings (
                firing_id TEXT PRIMARY KEY, trigger_id TEXT NOT NULL, user_id TEXT NOT NULL,
                source_key TEXT NOT NULL, run_id TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}',
                fired_at TEXT NOT NULL,
                FOREIGN KEY (trigger_id) REFERENCES task_triggers(trigger_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                UNIQUE (trigger_id, source_key)
            );
            CREATE TABLE IF NOT EXISTS task_run_commands (
                command_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, user_id TEXT NOT NULL,
                command_type TEXT NOT NULL, instruction TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending', idempotency_key TEXT, created_at TEXT NOT NULL,
                acknowledged_at TEXT,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (run_id, user_id, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS idx_task_triggers_owner_status
                ON task_triggers(user_id, status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_task_run_commands_pending
                ON task_run_commands(run_id, status, created_at);
        """
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)

    def _add_context_access_explanations(self, conn: sqlite3.Connection) -> None:
        """Persist non-content receipts explaining how personal context was selected."""
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(context_access_audit)").fetchall()
        }
        additions = {
            "source_decisions": "TEXT NOT NULL DEFAULT '[]'",
            "selected_references": "TEXT NOT NULL DEFAULT '[]'",
            "omitted_sections": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column, definition in additions.items():
            if column not in columns:
                conn.execute(
                    f"ALTER TABLE context_access_audit ADD COLUMN {column} {definition}"
                )


    def _add_personal_context_and_memories(self, conn: sqlite3.Connection) -> None:
        """Add permissioned companion settings, categorized memories, and access audit."""
        schema = """
            CREATE TABLE IF NOT EXISTS companion_settings (
                owner_id TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                tone TEXT NOT NULL DEFAULT 'calm',
                initiative TEXT NOT NULL DEFAULT 'balanced',
                permissions TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS personal_memories (
                memory_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_ref TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                use_in_context INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS context_access_audit (
                audit_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                requested_sections TEXT NOT NULL DEFAULT '[]',
                included_sections TEXT NOT NULL DEFAULT '[]',
                item_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_personal_memories_owner_status
                ON personal_memories(owner_id, status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_personal_memories_owner_type
                ON personal_memories(owner_id, memory_type, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_context_access_owner_created
                ON context_access_audit(owner_id, created_at DESC);
        """
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)


    def _add_profile_cognition(self, conn: sqlite3.Connection) -> None:
        """Add explainable profile observations, claims, and user overrides."""
        schema = """
            CREATE TABLE IF NOT EXISTS profile_observations (
                observation_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                summary TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_ref TEXT,
                attributes TEXT NOT NULL DEFAULT '{}',
                weight REAL NOT NULL DEFAULT 1.0,
                observed_at TEXT NOT NULL,
                sensitivity TEXT NOT NULL DEFAULT 'private',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS profile_claims (
                claim_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                profile_key TEXT NOT NULL,
                value TEXT,
                summary TEXT NOT NULL,
                rationale TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.5,
                review_status TEXT NOT NULL DEFAULT 'pending',
                evidence_refs TEXT NOT NULL DEFAULT '[]',
                first_observed_at TEXT,
                last_observed_at TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (owner_id, domain, profile_key)
            );
            CREATE TABLE IF NOT EXISTS profile_overrides (
                override_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                profile_key TEXT NOT NULL,
                operation TEXT NOT NULL,
                value TEXT,
                reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (owner_id, domain, profile_key)
            );
            CREATE INDEX IF NOT EXISTS idx_profile_observations_owner_status
                ON profile_observations(owner_id, status, observed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_profile_claims_owner_review
                ON profile_claims(owner_id, status, review_status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_profile_claims_owner_domain
                ON profile_claims(owner_id, domain, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_profile_overrides_owner_status
                ON profile_overrides(owner_id, status, updated_at DESC);
        """
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)


    def _migrate_to_layered_profile_cognition(self, conn: sqlite3.Connection) -> None:
        """Replace flat profile claims with layered, owner-scoped cognition records.

        Inputs:
            conn: SQLite connection at schema version 31, which may contain the
                former observations, claims, and override tables.
        Outputs:
            Canonical signal, pattern, hypothesis, facet, feedback, and
            suppression tables. Legacy rows are preserved as immutable audit
            snapshots, then the former live tables are removed.
        Called by:
            The ordered database migration runner during application startup.
        Invariants:
            Confirmed or corrected understandings become facets; rejected
            understandings become suppressions. Historical pending claims are
            archived because they were created under an older inference
            contract and cannot be presented as current review candidates.
        """
        schema = """
            CREATE TABLE IF NOT EXISTS profile_signals (
                signal_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                summary TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_ref TEXT,
                attributes TEXT NOT NULL DEFAULT '{}',
                weight REAL NOT NULL DEFAULT 1.0,
                observed_at TEXT NOT NULL,
                sensitivity TEXT NOT NULL DEFAULT 'private',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (owner_id, source_type, source_ref)
            );
            CREATE TABLE IF NOT EXISTS profile_patterns (
                pattern_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                pattern_key TEXT NOT NULL,
                label TEXT NOT NULL,
                detail TEXT NOT NULL,
                evidence_refs TEXT NOT NULL DEFAULT '[]',
                confidence REAL NOT NULL DEFAULT 0.5,
                status TEXT NOT NULL DEFAULT 'active',
                first_observed_at TEXT,
                last_observed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (owner_id, pattern_key)
            );
            CREATE TABLE IF NOT EXISTS profile_hypotheses (
                hypothesis_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                profile_key TEXT NOT NULL,
                value TEXT,
                summary TEXT NOT NULL,
                rationale TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.5,
                evidence_refs TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending',
                first_observed_at TEXT,
                last_observed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (owner_id, domain, profile_key)
            );
            CREATE TABLE IF NOT EXISTS profile_facets (
                facet_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                profile_key TEXT NOT NULL,
                label TEXT NOT NULL,
                value TEXT,
                source TEXT NOT NULL,
                source_hypothesis_id TEXT,
                context_enabled INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (owner_id, domain, profile_key)
            );
            CREATE TABLE IF NOT EXISTS profile_feedback (
                feedback_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                hypothesis_id TEXT,
                domain TEXT NOT NULL,
                profile_key TEXT NOT NULL,
                decision TEXT NOT NULL,
                value TEXT,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS profile_suppressions (
                suppression_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                profile_key TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (owner_id, domain, profile_key)
            );
            CREATE TABLE IF NOT EXISTS profile_legacy_records (
                legacy_record_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                record_type TEXT NOT NULL,
                legacy_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                migrated_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (record_type, legacy_id)
            );
            CREATE INDEX IF NOT EXISTS idx_profile_signals_owner_status
                ON profile_signals(owner_id, status, observed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_profile_patterns_owner_status
                ON profile_patterns(owner_id, status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_profile_hypotheses_owner_status
                ON profile_hypotheses(owner_id, status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_profile_facets_owner_status
                ON profile_facets(owner_id, status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_profile_feedback_owner_created
                ON profile_feedback(owner_id, created_at DESC);
        """
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if not {"profile_observations", "profile_claims", "profile_overrides"} & tables:
            return

        now = datetime.now(timezone.utc).isoformat()
        legacy_sources = (
            ("profile_observations", "observation_id", "signal"),
            ("profile_claims", "claim_id", "claim"),
            ("profile_overrides", "override_id", "override"),
        )
        for table, id_column, record_type in legacy_sources:
            if table not in tables:
                continue
            for row in conn.execute(f"SELECT * FROM {table}").fetchall():
                payload = dict(row)
                legacy_id = str(payload[id_column])
                conn.execute(
                    """INSERT OR IGNORE INTO profile_legacy_records
                       (legacy_record_id, owner_id, record_type, legacy_id, payload, migrated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (f"legacy:{record_type}:{legacy_id}", payload["owner_id"], record_type,
                     legacy_id, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), now),
                )

        if "profile_observations" in tables:
            conn.execute(
                """INSERT OR IGNORE INTO profile_signals
                   (signal_id, owner_id, kind, summary, source_type, source_ref, attributes,
                    weight, observed_at, sensitivity, status, created_at, updated_at)
                   SELECT observation_id, owner_id, kind, summary, source_type, source_ref, attributes,
                          weight, observed_at, sensitivity, status, created_at, updated_at
                   FROM profile_observations"""
            )

        if "profile_claims" in tables:
            conn.execute(
                """INSERT OR IGNORE INTO profile_hypotheses
                   (hypothesis_id, owner_id, domain, profile_key, value, summary, rationale,
                    confidence, evidence_refs, status, first_observed_at, last_observed_at,
                    created_at, updated_at)
                   SELECT claim_id, owner_id, domain, profile_key, value, summary, rationale,
                          confidence, evidence_refs,
                          'archived',
                          first_observed_at, last_observed_at, created_at, updated_at
                   FROM profile_claims"""
            )
            conn.execute(
                """INSERT OR IGNORE INTO profile_facets
                   (facet_id, owner_id, domain, profile_key, label, value, source,
                    source_hypothesis_id, context_enabled, status, created_at, updated_at)
                   SELECT 'facet:' || claim_id, owner_id, domain, profile_key, summary, value,
                          CASE review_status WHEN 'corrected' THEN 'user_corrected'
                                             ELSE 'user_confirmed' END,
                          claim_id, 1, 'active', created_at, updated_at
                   FROM profile_claims
                   WHERE status = 'active' AND review_status IN ('confirmed', 'corrected')"""
            )
            conn.execute(
                """INSERT OR IGNORE INTO profile_suppressions
                   (suppression_id, owner_id, domain, profile_key, reason, status, created_at, updated_at)
                   SELECT 'suppression:' || claim_id, owner_id, domain, profile_key, '',
                          'active', created_at, updated_at
                   FROM profile_claims
                   WHERE status = 'active' AND review_status = 'rejected'"""
            )

        if "profile_overrides" in tables:
            rows = conn.execute("SELECT * FROM profile_overrides WHERE status = 'active'").fetchall()
            for row in rows:
                override = dict(row)
                if override["operation"] == "suppress":
                    conn.execute(
                        """INSERT INTO profile_suppressions
                           (suppression_id, owner_id, domain, profile_key, reason, status, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                           ON CONFLICT(owner_id, domain, profile_key) DO UPDATE SET
                               reason = excluded.reason, status = 'active', updated_at = excluded.updated_at""",
                        (f"suppression:{override['override_id']}", override["owner_id"],
                         override["domain"], override["profile_key"], override["reason"],
                         override["created_at"], override["updated_at"]),
                    )
                elif override["operation"] == "replace":
                    conn.execute(
                        """INSERT INTO profile_facets
                           (facet_id, owner_id, domain, profile_key, label, value, source,
                            source_hypothesis_id, context_enabled, status, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, 'user_corrected', NULL, 1, 'active', ?, ?)
                           ON CONFLICT(owner_id, domain, profile_key) DO UPDATE SET
                               value = excluded.value, source = 'user_corrected',
                               context_enabled = 1, status = 'active', updated_at = excluded.updated_at""",
                        (f"facet:override:{override['override_id']}", override["owner_id"],
                         override["domain"], override["profile_key"], "已修正的协作偏好", override["value"],
                         override["created_at"], override["updated_at"]),
                    )

        for table in ("profile_observations", "profile_claims", "profile_overrides"):
            if table in tables:
                conn.execute(f"DROP TABLE {table}")

    def _retire_legacy_profile_candidates(self, conn: sqlite3.Connection) -> None:
        """Archive claims produced by the retired profile inference contract.

        Inputs:
            conn: SQLite connection with the layered profile schema and its
                immutable ``profile_legacy_records`` audit snapshots.
        Outputs:
            Historical pending claims become archived, while confirmed facets
            remain available as user-approved context.
        Called by:
            The ordered migration runner when upgrading databases that had
            already received migration 32.
        Invariants:
            No row originating in the former ``profile_claims`` table can
            appear as a live review candidate or enter an AI context.
        """
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if {"profile_hypotheses", "profile_legacy_records"}.issubset(tables):
            conn.execute(
                """UPDATE profile_hypotheses
                   SET status = 'archived', updated_at = ?
                   WHERE status = 'pending'
                     AND EXISTS (
                         SELECT 1 FROM profile_legacy_records AS legacy
                         WHERE legacy.owner_id = profile_hypotheses.owner_id
                           AND legacy.record_type = 'claim'
                           AND legacy.legacy_id = profile_hypotheses.hypothesis_id
                     )""",
                (datetime.now(timezone.utc).isoformat(),),
            )

        if "profile_facets" in tables:
            conn.execute(
                """UPDATE profile_facets
                   SET label = '已修正的协作偏好'
                   WHERE label = '你修正过的理解'"""
            )

    def _add_knowledge_document_retention(self, conn: sqlite3.Connection) -> None:
        """Add reversible retention state for personal knowledge sources."""
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(user_documents)").fetchall()
        }
        if "is_active" not in columns:
            conn.execute(
                "ALTER TABLE user_documents ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
            )
        if "archived_at" not in columns:
            conn.execute("ALTER TABLE user_documents ADD COLUMN archived_at TEXT")
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_user_documents_owner_retention
               ON user_documents(user_id, is_active, created_at DESC)"""
        )

    def _add_identity_security_sessions(self, conn: sqlite3.Connection) -> None:
        """Add durable per-device refresh sessions and token invalidation state."""
        user_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "token_version" not in user_columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"
            )
        if "password_changed_at" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_changed_at TEXT")

        conn.execute(
            """CREATE TABLE IF NOT EXISTS auth_sessions (
                   session_id TEXT PRIMARY KEY,
                   user_id TEXT NOT NULL,
                   refresh_token_hash TEXT NOT NULL,
                   expires_at TEXT NOT NULL,
                   created_at TEXT NOT NULL,
                   last_used_at TEXT,
                   revoked_at TEXT,
                   user_agent TEXT,
                   ip_address TEXT,
                   FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
               )"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_active
               ON auth_sessions(user_id, revoked_at, expires_at DESC)"""
        )

    def _add_reward_marketplace_integrity(self, conn: sqlite3.Connection) -> None:
        """Preserve immutable migration-3 history while initializing the points ledger index.

        Migration names are part of the validated database history and cannot be renamed.
        Fresh databases no longer create marketplace tables, so this historical migration
        only creates the still-required growth-ledger index.
        """
        ledger_table = "growth_point_ledger" if self._table_exists(conn, "growth_point_ledger") else "coins"
        index_name = "idx_growth_point_ledger_user_created_at" if ledger_table == "growth_point_ledger" else "idx_coins_user_created_at"
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS {index_name} ON {ledger_table}(user_id, created_at)"
        )


    def _add_durable_knowledge_jobs(self, conn: sqlite3.Connection) -> None:
        """Upgrade historical ingestion rows into recoverable, lease-aware knowledge jobs.

        Inputs:
            conn: Migration transaction connection supplied by Database.init_database.
        Outputs:
            None. The schema contract gains job type, progress, cancellation, worker lease, and result fields.
        Called by:
            Schema migration 28 exactly once per database.
        Side effects:
            Backfills deterministic state for legacy rows and creates claim/recovery indexes.
        Failure:
            Any SQLite failure aborts the surrounding migration transaction.
        Invariants:
            Existing version, trace, and ingestion history remains readable; no document source is removed.
        """
        columns = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_ingestion_jobs)").fetchall()}
        additions = {
            "job_type": "TEXT NOT NULL DEFAULT 'ingest' CHECK (job_type IN ('ingest', 'rebuild'))",
            "stage": "TEXT NOT NULL DEFAULT 'queued'",
            "progress": "INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100)",
            "attempt_count": "INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0)",
            "cancel_requested": "INTEGER NOT NULL DEFAULT 0 CHECK (cancel_requested IN (0, 1))",
            "worker_id": "TEXT",
            "lease_token": "TEXT",
            "lease_expires_at": "TEXT",
            "heartbeat_at": "TEXT",
            "result": "TEXT",
        }
        for column, definition in additions.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE knowledge_ingestion_jobs ADD COLUMN {column} {definition}")

        conn.execute(
            """UPDATE knowledge_ingestion_jobs
               SET stage = CASE
                   WHEN status = 'completed' THEN 'completed'
                   WHEN status = 'failed' THEN 'failed'
                   WHEN status = 'processing' THEN 'queued'
                   ELSE COALESCE(NULLIF(stage, ''), 'queued')
               END,
               progress = CASE
                   WHEN status = 'completed' THEN 100
                   WHEN progress < 0 THEN 0
                   WHEN progress > 100 THEN 100
                   ELSE progress
               END,
               worker_id = CASE WHEN status = 'processing' THEN NULL ELSE worker_id END,
               lease_token = CASE WHEN status = 'processing' THEN NULL ELSE lease_token END,
               lease_expires_at = CASE WHEN status = 'processing' THEN NULL ELSE lease_expires_at END,
               heartbeat_at = CASE WHEN status = 'processing' THEN NULL ELSE heartbeat_at END,
               status = CASE WHEN status = 'processing' THEN 'queued' ELSE status END"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_knowledge_ingestion_jobs_claim
               ON knowledge_ingestion_jobs(status, cancel_requested, lease_expires_at, created_at)"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_knowledge_ingestion_jobs_owner_updated
               ON knowledge_ingestion_jobs(owner_id, updated_at DESC)"""
        )

    def _unify_knowledge_document_catalog(self, conn: sqlite3.Connection) -> None:
        """Create the canonical document catalog and migrate legacy source rows.

        Inputs:
            conn: Migration transaction connection supplied by Database.init_database.
        Outputs:
            None. Private and official document metadata is available through one table.
        Called by:
            Schema migration 29 exactly once per database.
        Side effects:
            Copies legacy user_documents and system_rag_documents rows without changing
            document IDs, source paths, or vector chunk IDs. Legacy tables remain read-only
            migration sources until a later, separately verified cleanup migration.
        Failure:
            Any SQLite error aborts the surrounding migration transaction.
        Invariants:
            visibility is private or official; private rows always retain an owner_id;
            official rows are catalog-owned and remain readable to every signed-in user.
        """
        conn.execute(
            """CREATE TABLE IF NOT EXISTS knowledge_documents (
                   document_id TEXT PRIMARY KEY,
                   visibility TEXT NOT NULL CHECK (visibility IN ('private', 'official')),
                   owner_id TEXT,
                   title TEXT NOT NULL,
                   file_name TEXT,
                   file_type TEXT,
                   file_size INTEGER NOT NULL DEFAULT 0,
                   storage_path TEXT,
                   encryption_version TEXT NOT NULL DEFAULT 'none',
                   parse_status TEXT NOT NULL DEFAULT 'pending',
                   index_collection TEXT,
                   chroma_ids TEXT NOT NULL DEFAULT '[]',
                   content_preview TEXT,
                   tags TEXT NOT NULL DEFAULT '[]',
                   description TEXT,
                   error_message TEXT,
                   is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
                   archived_at TEXT,
                   created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                   updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                   CHECK ((visibility = 'private' AND owner_id IS NOT NULL AND owner_id != '')
                       OR visibility = 'official')
               )"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_knowledge_documents_visibility_owner_active
               ON knowledge_documents(visibility, owner_id, is_active, created_at DESC)"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_knowledge_documents_visibility_status
               ON knowledge_documents(visibility, parse_status, is_active)"""
        )

        if self._table_exists(conn, "user_documents"):
            source_columns = {row[1] for row in conn.execute("PRAGMA table_info(user_documents)").fetchall()}
            archived_at = "archived_at" if "archived_at" in source_columns else "NULL"
            is_active = "is_active" if "is_active" in source_columns else "1"
            conn.execute(
                f"""INSERT OR IGNORE INTO knowledge_documents (
                       document_id, visibility, owner_id, title, file_name, file_type,
                       file_size, storage_path, encryption_version, parse_status, index_collection, chroma_ids,
                       content_preview, tags, description, error_message, is_active,
                       archived_at, created_at, updated_at
                   )
                   SELECT doc_id, 'private', user_id, title, original_name, file_type,
                          COALESCE(file_size, 0), storage_path, 'none', COALESCE(parse_status, 'pending'),
                          vector_collection, COALESCE(chroma_ids, '[]'), content_preview,
                          COALESCE(tags, '[]'), NULL, error_message, COALESCE({is_active}, 1),
                          {archived_at}, COALESCE(created_at, CURRENT_TIMESTAMP),
                          COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
                   FROM user_documents"""
            )

        if self._table_exists(conn, "system_rag_documents"):
            source_columns = {row[1] for row in conn.execute("PRAGMA table_info(system_rag_documents)").fetchall()}
            updated_at = "updated_at" if "updated_at" in source_columns else "upload_time"
            conn.execute(
                f"""INSERT OR IGNORE INTO knowledge_documents (
                       document_id, visibility, owner_id, title, file_name, file_type,
                       file_size, storage_path, encryption_version, parse_status, index_collection, chroma_ids,
                       content_preview, tags, description, error_message, is_active,
                       archived_at, created_at, updated_at
                   )
                   SELECT id, 'official', COALESCE(uploaded_by, 'system'), title, file_name,
                          file_type, COALESCE(file_size, 0), NULL, 'not_stored',
                          COALESCE(parse_status, 'completed'), 'system_knowledge',
                          COALESCE(chroma_ids, '[]'), NULL, COALESCE(tags, '[]'),
                          description, error_message, COALESCE(is_active, 1), NULL,
                          COALESCE(upload_time, CURRENT_TIMESTAMP),
                          COALESCE({updated_at}, upload_time, CURRENT_TIMESTAMP)
                   FROM system_rag_documents"""
            )

    def _add_knowledge_private_content_encryption(self, conn: sqlite3.Connection) -> None:
        """Track at-rest encryption for private source and vector content.

        Private source files are migrated by the application after this schema
        change. The column prevents a restart from repeatedly rebuilding an
        already encrypted Chroma index.
        """
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(knowledge_documents)").fetchall()}
        if "index_encryption_version" not in columns:
            conn.execute(
                "ALTER TABLE knowledge_documents "
                "ADD COLUMN index_encryption_version TEXT NOT NULL DEFAULT 'none'"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_private_encryption "
            "ON knowledge_documents(visibility, encryption_version, index_encryption_version)"
        )

    def _add_user_library_entries(self, conn: sqlite3.Connection) -> None:
        """Record a user's references to shared library materials without copying content.

        Inputs: the migration connection with the canonical knowledge_documents
        catalog already installed. Outputs: a unique user-to-shared-document
        relationship. Called once by schema migration 31.
        Side effects: creates only lightweight relationship rows; source files,
        document metadata, and Chroma chunks remain single global instances.
        """
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_library_entries (
                   user_id TEXT NOT NULL,
                   document_id TEXT NOT NULL,
                   created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                   PRIMARY KEY (user_id, document_id),
                   FOREIGN KEY (document_id) REFERENCES knowledge_documents(document_id)
                       ON DELETE CASCADE
               )"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_user_library_entries_user_created
               ON user_library_entries(user_id, created_at DESC)"""
        )

    def _add_knowledge_engine_lifecycle(self, conn: sqlite3.Connection) -> None:
        """Add durable knowledge ingestion and retrieval trace records."""
        conn.execute(
            """CREATE TABLE IF NOT EXISTS knowledge_document_versions (
                   version_id TEXT PRIMARY KEY,
                   document_id TEXT NOT NULL,
                   owner_id TEXT NOT NULL,
                   content_fingerprint TEXT NOT NULL,
                   source_size INTEGER NOT NULL DEFAULT 0,
                   index_version TEXT NOT NULL,
                   created_at TEXT NOT NULL
               )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS knowledge_ingestion_jobs (
                   job_id TEXT PRIMARY KEY,
                   version_id TEXT NOT NULL,
                   document_id TEXT NOT NULL,
                   owner_id TEXT NOT NULL,
                   status TEXT NOT NULL,
                   chunk_count INTEGER,
                   index_version TEXT,
                   error_message TEXT,
                   created_at TEXT NOT NULL,
                   updated_at TEXT NOT NULL,
                   completed_at TEXT,
                   FOREIGN KEY (version_id) REFERENCES knowledge_document_versions(version_id)
                       ON DELETE CASCADE
               )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS knowledge_retrieval_traces (
                   trace_id TEXT PRIMARY KEY,
                   owner_id TEXT NOT NULL,
                   question TEXT NOT NULL,
                   mode TEXT NOT NULL,
                   candidate_count INTEGER NOT NULL,
                   ranked_count INTEGER NOT NULL,
                   citations TEXT NOT NULL,
                   created_at TEXT NOT NULL
               )"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_knowledge_versions_document_owner
               ON knowledge_document_versions(document_id, owner_id, created_at DESC)"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_knowledge_ingestion_document_owner
               ON knowledge_ingestion_jobs(document_id, owner_id, created_at DESC)"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_knowledge_traces_owner_created
               ON knowledge_retrieval_traces(owner_id, created_at DESC)"""
        )

    def _add_task_workspace_generation_state(self, conn: sqlite3.Connection) -> None:
        """Historical migration for databases that still contain retired task chains."""
        if not self._table_exists(conn, "task_chains"):
            return
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(task_chains)").fetchall()
        }
        if "generation_status" not in columns:
            conn.execute(
                "ALTER TABLE task_chains ADD COLUMN generation_status TEXT NOT NULL DEFAULT 'ready'"
            )
        if "generation_error" not in columns:
            conn.execute("ALTER TABLE task_chains ADD COLUMN generation_error TEXT")

    def _create_initial_schema(self, conn: sqlite3.Connection) -> None:
        """Create the legacy-compatible baseline inside the migration transaction."""
        cursor = conn.cursor()

        # 用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            learning_goal TEXT,
            specialization TEXT,
            level INTEGER DEFAULT 1,
            role TEXT DEFAULT 'user',  -- 新增角色字段：user/admin/editor
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
        ''')

        # 确保旧数据库也有新字段
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN learning_goal TEXT")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN specialization TEXT")
        except:
            pass

        # 属性表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attributes (
            attr_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            attr_name TEXT NOT NULL,
            attr_value INTEGER DEFAULT 0,
            max_value INTEGER DEFAULT 100,
            description TEXT,
            icon TEXT DEFAULT '📊',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # Durable growth-point activity. Points are an audit record, not currency.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS growth_point_ledger (
            record_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        # A completed Step settles at most one immutable points amount.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_reward_settlements (
            settlement_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            step_id TEXT NOT NULL,
            growth_points INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, step_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # 系统RAG文档表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_rag_documents (
            id VARCHAR(36) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            file_name VARCHAR(255),
            file_type VARCHAR(10),
            file_size INTEGER,
            chroma_ids TEXT,  -- 存储Chroma中的向量ID列表
            uploaded_by VARCHAR(36),  -- 管理员ID
            upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            parse_status TEXT DEFAULT 'completed', -- 'processing', 'completed', 'failed'
            error_message TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            tags JSON,  -- 标签数组
            description TEXT,
            version INTEGER DEFAULT 1
        )
        ''')

        # 用户会话临时文件表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_session_files (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            session_id VARCHAR(36) NOT NULL,
            file_name VARCHAR(255),
            content_preview TEXT,  -- 仅存储前500字符
            original_size INTEGER,
            upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME,  -- 24小时后过期
            is_processed BOOLEAN DEFAULT FALSE,
            storage_path TEXT,
            mime_type TEXT
        )
        ''')
        try:
            cursor.execute("ALTER TABLE user_session_files ADD COLUMN storage_path TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE user_session_files ADD COLUMN mime_type TEXT")
        except Exception:
            pass

        # 聊天分组表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_groups (
            group_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            group_name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # 聊天会话表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            session_name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES chat_groups(group_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # 聊天消息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens INTEGER DEFAULT 0,
            reply_to_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # 用户文档表 - 虚空系统文档管理
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_documents (
            doc_id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            title VARCHAR(255) NOT NULL,
            original_name VARCHAR(255),
            file_type VARCHAR(10),
            file_size INTEGER,
            storage_path TEXT,
            parse_status TEXT DEFAULT 'pending',
            vector_collection TEXT,  -- 用户专属向量集合名
            chroma_ids TEXT,         -- Chroma向量ID列表(JSON)
            content_preview TEXT,
            tags JSON,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # 文档版本表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_document_versions (
            version_id VARCHAR(36) PRIMARY KEY,
            doc_id VARCHAR(36) NOT NULL,
            version_number INTEGER DEFAULT 1,
            file_path TEXT,
            changes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES user_documents(doc_id) ON DELETE CASCADE
        )
        ''')

        # 添加用户会话临时文件表索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_session ON user_session_files(user_id, session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires ON user_session_files(expires_at)')

        # 添加索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attributes_user_id ON attributes(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_growth_point_ledger_user_id ON growth_point_ledger(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_rag_documents_uploaded_by ON system_rag_documents(uploaded_by)")

        # 为 system_rag_documents 添加新字段
        try:
            cursor.execute("ALTER TABLE system_rag_documents ADD COLUMN parse_status TEXT DEFAULT 'completed'")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE system_rag_documents ADD COLUMN error_message TEXT")
        except:
            pass

        # 用户文档相关索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_documents_status ON user_documents(parse_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_documents_created ON user_documents(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_document_versions_doc_id ON user_document_versions(doc_id)")

        # 聊天相关索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_groups_user_id ON chat_groups(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_group_id ON chat_sessions(group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)")


    def _add_runtime_columns_and_indexes(self, conn: sqlite3.Connection) -> None:
        """Add columns and indexes required by current runtime invariants."""
        user_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "is_active" not in user_columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
            )

        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_chat_sessions_owner_group
               ON chat_sessions(user_id, group_id, updated_at)"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_chat_messages_owner_session
               ON chat_messages(user_id, session_id, created_at)"""
        )

    def ensure_default_admin(
        self,
        username: str,
        email: str,
        password_hash: str,
        user_id: str = "0000",
    ) -> bool:
        """Create the bootstrap administrator explicitly from application startup."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT 1 FROM users WHERE user_id = ? OR username = ?",
                (user_id, username),
            )
            if cursor.fetchone():
                return False
            cursor.execute(
                """INSERT INTO users
                   (user_id, username, email, password_hash, role)
                   VALUES (?, ?, ?, ?, 'admin')""",
                (user_id, username, email, password_hash),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== 身份会话相关方法 ====================
    def create_auth_session(
        self,
        session_id: str,
        user_id: str,
        refresh_token_hash: str,
        expires_at: str,
        created_at: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Persist the current refresh token for one device session."""
        conn = self.get_connection()
        try:
            conn.execute(
                """INSERT INTO auth_sessions
                   (session_id, user_id, refresh_token_hash, expires_at, created_at,
                    user_agent, ip_address)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, user_id, refresh_token_hash, expires_at, created_at, user_agent, ip_address),
            )
            conn.commit()
        finally:
            conn.close()

    def get_auth_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Return one owned authentication session."""
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM auth_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def rotate_auth_session(
        self,
        session_id: str,
        user_id: str,
        expected_refresh_hash: str,
        replacement_refresh_hash: str,
        expires_at: str,
        used_at: str,
    ) -> bool:
        """Atomically rotate a refresh token and reject a replayed predecessor."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                """UPDATE auth_sessions
                   SET refresh_token_hash = ?, expires_at = ?, last_used_at = ?
                   WHERE session_id = ? AND user_id = ?
                     AND refresh_token_hash = ? AND revoked_at IS NULL
                     AND expires_at > ?""",
                (replacement_refresh_hash, expires_at, used_at, session_id, user_id, expected_refresh_hash, used_at),
            )
            conn.commit()
            return cursor.rowcount == 1
        finally:
            conn.close()

    def revoke_auth_session(self, session_id: str, user_id: str, revoked_at: str) -> bool:
        """Revoke the active session on one device."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                """UPDATE auth_sessions SET revoked_at = ?
                   WHERE session_id = ? AND user_id = ? AND revoked_at IS NULL""",
                (revoked_at, session_id, user_id),
            )
            conn.commit()
            return cursor.rowcount == 1
        finally:
            conn.close()

    def revoke_all_auth_sessions(self, user_id: str, revoked_at: str) -> int:
        """Revoke all active device sessions owned by one user."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (revoked_at, user_id),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def update_user_password(self, user_id: str, password_hash: str, changed_at: str) -> bool:
        """Rotate password and invalidate every outstanding token version."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                """UPDATE users
                   SET password_hash = ?, password_changed_at = ?, token_version = token_version + 1
                   WHERE user_id = ?""",
                (password_hash, changed_at, user_id),
            )
            conn.commit()
            return cursor.rowcount == 1
        finally:
            conn.close()

    # ==================== 用户相关方法 ====================
    def _generate_next_uid(self, cursor: sqlite3.Cursor) -> str:
        """生成下一个连续的UID"""
        # 获取除了0000(管理员)之外的UID
        cursor.execute("SELECT user_id FROM users WHERE user_id != '0000'")
        existing_uids = [row[0] for row in cursor.fetchall()]

        # 只筛选出纯数字的UID以兼容以前的UUID
        numeric_uids = [int(uid) for uid in existing_uids if uid.isdigit()]

        if not numeric_uids:
            return "1001"

        return str(max(numeric_uids) + 1)

    def add_user(
        self,
        username: str,
        email: Optional[str] = None,
        password_hash: Optional[str] = None
    ) -> Optional[str]:
        """添加新用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            user_id = self._generate_next_uid(cursor)
            cursor.execute(
                "INSERT INTO users (user_id, username, email, password_hash) VALUES (?, ?, ?, ?)",
                (user_id, username, email, password_hash)
            )
            conn.commit()
            return user_id
        except sqlite3.IntegrityError as e:
            logger.error(f"添加用户失败: {e}")
            return None
        finally:
            conn.close()

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过邮箱获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过用户ID获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def update_last_login(self, user_id: str) -> None:
        """更新用户最后登录时间"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE user_id = ?",
                (datetime.now().isoformat(), user_id)
            )
            conn.commit()
        finally:
            conn.close()

    def update_user_info(self, user_id: str,
                        email: Optional[str] = None, learning_goal: Optional[str] = None,
                        specialization: Optional[str] = None, username: Optional[str] = None,
                        role: Optional[str] = None) -> bool:
        """更新用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates: List[str] = []
            params: List[Any] = []

            if username is not None:
                updates.append("username = ?")
                params.append(username)
            if email is not None:
                updates.append("email = ?")
                params.append(email)
            if learning_goal is not None:
                updates.append("learning_goal = ?")
                params.append(learning_goal)
            if specialization is not None:
                updates.append("specialization = ?")
                params.append(specialization)
            if role is not None:
                updates.append("role = ?")
                params.append(role)

            if not updates:
                return False

            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_user_profile(self, user_id: str,
                           email: Optional[str] = None, learning_goal: Optional[str] = None,
                           specialization: Optional[str] = None, username: Optional[str] = None) -> bool:
        """更新用户资料"""
        return self.update_user_info(user_id, email, learning_goal, specialization, username)

    # ==================== 属性相关方法 ====================
    def add_attribute(
        self,
        user_id: str,
        attr_name: str,
        max_value: int = 100,
        description: str = "",
        icon: str = "📊"
    ) -> str:
        """
        添加用户属性
        Args:
            user_id: 用户ID
            attr_name: 属性名称
            max_value: 最大值，默认100
            description: 属性描述
            icon: 属性图标
        Returns:
            新创建的属性ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        attr_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        try:
            cursor.execute(
                """INSERT INTO attributes
                   (attr_id, user_id, attr_name, max_value, description, icon, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (attr_id, user_id, attr_name, max_value, description, icon, now, now)
            )
            conn.commit()
            return attr_id
        finally:
            conn.close()

    def get_user_attributes(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户所有属性
        Args:
            user_id: 用户ID
        Returns:
            属性列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM attributes WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def update_attribute_value(self, attr_id: str, value: int) -> int:
        """
        更新属性值
        Args:
            attr_id: 属性ID
            value: 新的属性值
        Returns:
            更新后的属性值（不超过最大值）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 先获取属性的最大值，确保不超过最大值
            cursor.execute(
                "SELECT max_value FROM attributes WHERE attr_id = ?",
                (attr_id,)
            )
            max_value_result = cursor.fetchone()
            if max_value_result:
                value = min(value, max_value_result[0])

            cursor.execute(
                "UPDATE attributes SET attr_value = ?, updated_at = ? WHERE attr_id = ?",
                (value, datetime.now().isoformat(), attr_id)
            )
            conn.commit()
            return value
        finally:
            conn.close()

    def update_attribute(
        self,
        attr_id: str,
        attr_name: Optional[str] = None,
        attr_value: Optional[int] = None,
        description: Optional[str] = None,
        max_value: Optional[int] = None,
    ) -> bool:
        """更新属性信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates: List[str] = []
            params: List[Any] = []

            if attr_name is not None:
                updates.append("attr_name = ?")
                params.append(attr_name)

            if attr_value is not None:
                updates.append("attr_value = ?")
                params.append(attr_value)

            if description is not None:
                updates.append("description = ?")
                params.append(description)

            if max_value is not None:
                updates.append("max_value = ?")
                params.append(max_value)

            if not updates:
                return False

            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(attr_id)

            query = f"UPDATE attributes SET {', '.join(updates)} WHERE attr_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_attribute(self, attr_id: str) -> bool:
        """删除属性"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM attributes WHERE attr_id = ?", (attr_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    # ==================== RAG文档管理相关方法 ====================
    def add_system_rag_document(
        self,
        title: str,
        uploaded_by: str,
        file_name: str = "",
        file_type: str = "",
        file_size: int = 0,
        chroma_ids: str = "",
        tags: Optional[List[str]] = None,
        description: str = "",
        parse_status: str = "completed",
        is_active: bool = True,
        doc_id: Optional[str] = None
    ) -> str:
        """
        添加系统RAG文档
        Args:
            title: 文档标题
            uploaded_by: 上传者ID
            file_name: 文件名
            file_type: 文件类型
            file_size: 文件大小
            chroma_ids: Chroma向量ID列表（JSON格式）
            tags: 标签列表
            description: 文档描述
            parse_status: 解析状态
            is_active: 是否激活
            doc_id: 预定义的文档ID（可选）
        Returns:
            新创建的文档ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        doc_id = doc_id or str(uuid.uuid4())
        tags_json = json.dumps(tags or [])
        try:
            cursor.execute(
                """INSERT INTO system_rag_documents
                   (id, title, file_name, file_type, file_size, chroma_ids, uploaded_by, tags, description, parse_status, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, title, file_name, file_type, file_size, chroma_ids, uploaded_by, tags_json, description, parse_status, 1 if is_active else 0)
            )
            conn.commit()
            return doc_id
        finally:
            conn.close()

    def get_system_rag_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个系统RAG文档
        Args:
            doc_id: 文档ID
        Returns:
            文档信息，不存在则返回None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM system_rag_documents WHERE id = ?",
                (doc_id,)
            )
            row = cursor.fetchone()
            if row:
                doc_dict = dict(row)
                # 解析JSON字段
                if doc_dict.get("tags"):
                    doc_dict["tags"] = json.loads(doc_dict["tags"])
                return doc_dict
            return None
        finally:
            conn.close()

    def list_system_rag_documents(self, filter_tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        列出所有系统RAG文档
        Args:
            filter_tags: 标签过滤（可选）
        Returns:
            文档列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM system_rag_documents WHERE is_active = 1 ORDER BY upload_time DESC"
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                doc_dict = dict(row)
                # 解析JSON字段
                if doc_dict.get("tags"):
                    try:
                        doc_dict["tags"] = json.loads(doc_dict["tags"])
                    except:
                        doc_dict["tags"] = []
                else:
                    doc_dict["tags"] = []

                # 在Python中执行标签过滤
                if filter_tags:
                    if not all(tag in doc_dict["tags"] for tag in filter_tags):
                        continue

                results.append(doc_dict)
            return results
        finally:
            conn.close()

    def get_all_system_rag_tags(self) -> List[str]:
        """
        获取所有系统RAG文档中使用到的所有唯一标签
        Returns:
            标签列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT tags FROM system_rag_documents WHERE is_active = 1")
            rows = cursor.fetchall()
            all_tags = set()
            for row in rows:
                if row[0]:
                    try:
                        tags = json.loads(row[0])
                        if isinstance(tags, list):
                            for tag in tags:
                                all_tags.add(tag)
                    except:
                        continue
            return sorted(list(all_tags))
        finally:
            conn.close()

    def update_system_rag_document(
        self,
        doc_id: str,
        title: Optional[str] = None,
        file_name: Optional[str] = None,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        chroma_ids: Optional[str] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        parse_status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新系统RAG文档
        Args:
            doc_id: 文档ID
            title: 文档标题（可选）
            file_name: 文件名（可选）
            file_type: 文件类型（可选）
            file_size: 文件大小（可选）
            chroma_ids: Chroma向量ID列表（可选）
            is_active: 是否激活（可选）
            tags: 标签列表（可选）
            description: 文档描述（可选）
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates: List[str] = []
            params: List[Any] = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)

            if file_name is not None:
                updates.append("file_name = ?")
                params.append(file_name)

            if file_type is not None:
                updates.append("file_type = ?")
                params.append(file_type)

            if file_size is not None:
                updates.append("file_size = ?")
                params.append(file_size)

            if chroma_ids is not None:
                updates.append("chroma_ids = ?")
                params.append(chroma_ids)

            if is_active is not None:
                updates.append("is_active = ?")
                params.append(is_active)

            if tags is not None:
                updates.append("tags = ?")
                params.append(json.dumps(tags))

            if description is not None:
                updates.append("description = ?")
                params.append(description)

            if parse_status is not None:
                updates.append("parse_status = ?")
                params.append(parse_status)

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if not updates:
                return False

            params.append(doc_id)
            query = f"UPDATE system_rag_documents SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_system_rag_document_status(
        self,
        doc_id: str,
        parse_status: Optional[str] = None,
        is_active: Optional[bool] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """快速更新系统文档状态"""
        return self.update_system_rag_document(
            doc_id=doc_id,
            parse_status=parse_status,
            is_active=is_active,
            error_message=error_message
        )

    def delete_old_task_history(self, days: int = 7) -> int:
        """
        删除超过指定天数的任务生成历史记录

        Args:
            days: 保留天数

        Returns:
            删除的记录数量
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # SQLite日期函数使用
            cursor.execute(
                "DELETE FROM task_generation_history WHERE created_at < datetime('now', '-' || ? || ' days')",
                (days,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
        finally:
            conn.close()

    def delete_system_rag_document(self, doc_id: str) -> bool:
        """
        删除系统RAG文档（软删除，将is_active设为False）
        Args:
            doc_id: 文档ID
        Returns:
            是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE system_rag_documents SET is_active = 0 WHERE id = ?",
                (doc_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # ==================== 临时文件管理相关方法 ====================
    # ... existing code ...

    # ==================== 用户文档管理相关方法 ====================
    def add_user_session_file(
        self,
        user_id: str,
        session_id: str,
        file_name: str,
        content_preview: str,
        original_size: int,
        file_id: Optional[str] = None,
        storage_path: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        """
        添加用户会话临时文件
        Args:
            user_id: 用户ID
            session_id: 会话ID
            file_name: 文件名
            content_preview: 内容预览（前500字符）
            original_size: 原始文件大小
            file_id: 可选预生成 ID（用于先落盘再入库）
            storage_path: 可选本地持久化路径（图片等多媒体）
            mime_type: 可选 MIME 类型
        Returns:
            新创建的文件ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        fid = file_id or str(uuid.uuid4())
        upload_time = datetime.now()
        expires_at = upload_time + timedelta(days=1)  # 24小时后过期
        try:
            cursor.execute(
                """INSERT INTO user_session_files
                   (id, user_id, session_id, file_name, content_preview, original_size, upload_time, expires_at, storage_path, mime_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (fid, user_id, session_id, file_name, content_preview, original_size,
                 upload_time.isoformat(), expires_at.isoformat(), storage_path, mime_type)
            )
            conn.commit()
            return fid
        finally:
            conn.close()

    def get_user_session_files(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """
        获取用户会话临时文件列表
        Args:
            user_id: 用户ID
            session_id: 会话ID
        Returns:
            临时文件列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT * FROM user_session_files
                   WHERE user_id = ? AND session_id = ? AND expires_at > ?
                   ORDER BY upload_time DESC""",
                (user_id, session_id, datetime.now().isoformat())
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_active_session_file_summaries(self, user_id: str) -> List[Dict[str, Any]]:
        """List owned chat sessions that still contain temporary attachments."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT files.session_id,
                          sessions.session_name,
                          sessions.group_id,
                          COUNT(files.id) AS file_count,
                          MAX(files.upload_time) AS last_upload_at,
                          MAX(files.expires_at) AS expires_at
                   FROM user_session_files AS files
                   JOIN chat_sessions AS sessions
                     ON sessions.session_id = files.session_id
                    AND sessions.user_id = files.user_id
                   WHERE files.user_id = ? AND files.expires_at > ?
                   GROUP BY files.session_id, sessions.session_name, sessions.group_id
                   ORDER BY last_upload_at DESC""",
                (user_id, datetime.now().isoformat()),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def cleanup_expired_session_files(self) -> int:
        """
        清理过期的会话临时文件
        Returns:
            清理的文件数量
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM user_session_files WHERE expires_at <= ?",
                (datetime.now().isoformat(),)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def list_expired_session_file_storage_paths(self) -> List[str]:
        """返回已过期记录的 storage_path（用于在删除行前清理磁盘）。"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT storage_path FROM user_session_files WHERE expires_at <= ? AND storage_path IS NOT NULL",
                (datetime.now().isoformat(),)
            )
            return [row[0] for row in cursor.fetchall() if row[0]]
        finally:
            conn.close()

    def user_owns_chat_session(self, session_id: str, user_id: str) -> bool:
        """当前用户是否拥有该聊天会话。"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT 1 FROM chat_sessions WHERE session_id = ? AND user_id = ? LIMIT 1",
                (session_id, user_id)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_user_session_file(self, user_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 获取单条会话临时文件记录。"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT * FROM user_session_files
                   WHERE id = ? AND user_id = ? AND expires_at > ?""",
                (file_id, user_id, datetime.now().isoformat())
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_user_session_file(self, user_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        """
        删除会话临时文件记录，返回被删行（含 storage_path）以便删磁盘。
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM user_session_files WHERE id = ? AND user_id = ?",
                (file_id, user_id)
            )
            row = cursor.fetchone()
            if not row:
                return None
            prev = dict(row)
            cursor.execute(
                "DELETE FROM user_session_files WHERE id = ? AND user_id = ?",
                (file_id, user_id)
            )
            conn.commit()
            return prev
        finally:
            conn.close()

    # ==================== 用户文档管理相关方法 ====================

    def add_user_document(self, user_id: str, title: str, original_name: str, file_type: str,
                         file_size: int, storage_path: str, content_preview: str = "",
                         tags: Optional[List[str]] = None, doc_id: Optional[str] = None) -> str:
        """
        添加用户文档记录
        Args:
            user_id: 用户ID
            title: 文档标题
            original_name: 原始文件名
            file_type: 文件类型
            file_size: 文件大小
            storage_path: 存储路径
            content_preview: 内容预览
            tags: 标签列表
        Returns:
            新创建的文档ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        doc_id = doc_id or str(uuid.uuid4())
        now = datetime.now().isoformat()

        try:
            cursor.execute(
                """INSERT INTO user_documents
                   (doc_id, user_id, title, original_name, file_type, file_size,
                    storage_path, content_preview, tags, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, user_id, title, original_name, file_type, file_size,
                 storage_path, content_preview, json.dumps(tags or []), now, now)
            )
            conn.commit()
            return doc_id
        finally:
            conn.close()

    def get_user_documents(self, user_id: str, status: Optional[str] = None,
                          limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取用户文档列表
        Args:
            user_id: 用户ID
            status: 解析状态筛选
            limit: 返回数量限制
            offset: 偏移量
        Returns:
            文档列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM user_documents WHERE user_id = ? AND is_active = 1"
            params = [user_id]

            if status:
                query += " AND parse_status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = []
            for row in rows:
                doc_dict = dict(row)
                # 解析JSON字段
                try:
                    doc_dict["tags"] = json.loads(doc_dict.get("tags", "[]"))
                    doc_dict["chroma_ids"] = json.loads(doc_dict.get("chroma_ids", "[]")) if doc_dict.get("chroma_ids") else []
                except json.JSONDecodeError:
                    doc_dict["tags"] = []
                    doc_dict["chroma_ids"] = []
                result.append(doc_dict)

            return result
        finally:
            conn.close()

    def get_user_document(self, user_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个用户文档
        Args:
            user_id: 用户ID
            doc_id: 文档ID
        Returns:
            文档信息或None
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM user_documents WHERE doc_id = ? AND user_id = ?",
                (doc_id, user_id)
            )
            row = cursor.fetchone()

            if row:
                doc_dict = dict(row)
                # 确保所有字段都有默认值，避免后续处理出错
                doc_dict.setdefault("tags", "[]")
                doc_dict.setdefault("chroma_ids", None)
                doc_dict.setdefault("storage_path", "")
                doc_dict.setdefault("vector_collection", "")

                # 安全解析JSON字段，即使解析出错也能返回文档信息
                try:
                    doc_dict["tags"] = json.loads(doc_dict["tags"])
                except (json.JSONDecodeError, TypeError):
                    doc_dict["tags"] = []

                try:
                    doc_dict["chroma_ids"] = json.loads(doc_dict["chroma_ids"]) if doc_dict["chroma_ids"] else []
                except (json.JSONDecodeError, TypeError):
                    doc_dict["chroma_ids"] = []

                return doc_dict

            return None
        except Exception as e:
            logger.error(f"获取单个文档失败 {user_id}:{doc_id}: {str(e)}")
            return None
        finally:
            conn.close()

    def update_user_document_status(self, doc_id: str, status: str,
                                   vector_collection: Optional[str] = None,
                                   chroma_ids: Optional[List[str]] = None,
                                   content_preview: Optional[str] = None,
                                   error_message: Optional[str] = None) -> bool:
        """
        更新文档解析状态
        Args:
            doc_id: 文档ID
            status: 新状态
            vector_collection: 向量集合名
            chroma_ids: Chroma向量ID列表
            content_preview: 内容预览
            error_message: 错误信息
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            updates = ["parse_status = ?", "updated_at = ?"]
            params = [status, datetime.now().isoformat()]

            if vector_collection is not None:
                updates.append("vector_collection = ?")
                params.append(vector_collection)

            if chroma_ids is not None:
                updates.append("chroma_ids = ?")
                params.append(json.dumps(chroma_ids))

            if content_preview is not None:
                updates.append("content_preview = ?")
                params.append(content_preview)

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            params.append(doc_id)

            query = f"UPDATE user_documents SET {', '.join(updates)} WHERE doc_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def update_user_document_info(self, doc_id: str, user_id: str, title: Optional[str] = None,
                                 tags: Optional[List[str]] = None) -> bool:
        """
        更新文档基本信息
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            title: 新标题
            tags: 新标签
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            updates = ["updated_at = ?"]
            params = [datetime.now().isoformat()]

            if title:
                updates.append("title = ?")
                params.append(title)

            if tags is not None:
                updates.append("tags = ?")
                params.append(json.dumps(tags))

            if len(updates) == 1:  # 只有时间更新
                return True

            params.extend([doc_id, user_id])
            query = f"UPDATE user_documents SET {', '.join(updates)} WHERE doc_id = ? AND user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_user_document(self, doc_id: str, user_id: str) -> bool:
        """
        删除用户文档
        Args:
            doc_id: 文档ID
            user_id: 用户ID
        Returns:
            是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 先检查文档是否存在
            cursor.execute(
                "SELECT doc_id FROM user_documents WHERE doc_id = ? AND user_id = ?",
                (doc_id, user_id)
            )
            if cursor.fetchone() is None:
                return False

            # 执行删除操作
            cursor.execute(
                "DELETE FROM user_documents WHERE doc_id = ? AND user_id = ?",
                (doc_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def check_document_exists(self, doc_id: str, user_id: str) -> bool:
        """
        检查文档是否存在
        Args:
            doc_id: 文档ID
            user_id: 用户ID
        Returns:
            文档是否存在
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT doc_id FROM user_documents WHERE doc_id = ? AND user_id = ?",
                (doc_id, user_id)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_user_document_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户文档统计信息
        Args:
            user_id: 用户ID
        Returns:
            统计信息
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 总文档数
            cursor.execute("SELECT COUNT(*) FROM user_documents WHERE user_id = ?", (user_id,))
            total_docs = cursor.fetchone()[0]

            # 各状态文档数
            cursor.execute("""
                SELECT parse_status, COUNT(*) as count
                FROM user_documents
                WHERE user_id = ?
                GROUP BY parse_status
            """, (user_id,))
            status_rows = cursor.fetchall()
            status_stats = {row[0]: row[1] for row in status_rows}

            # 总存储大小
            cursor.execute("SELECT SUM(file_size) FROM user_documents WHERE user_id = ?", (user_id,))
            total_size = cursor.fetchone()[0] or 0

            return {
                "total_documents": total_docs,
                "status_stats": status_stats,
                "total_size": total_size,
                "completed_documents": status_stats.get("completed", 0)
            }
        finally:
            conn.close()

    # ==================== 智能助手对话持久化方法 ====================

    def add_chat_group(self, user_id: str, group_name: str) -> str:
        """创建新的对话分组"""
        conn = self.get_connection()
        cursor = conn.cursor()
        group_id = str(uuid.uuid4())
        try:
            cursor.execute(
                "INSERT INTO chat_groups (group_id, user_id, group_name) VALUES (?, ?, ?)",
                (group_id, user_id, group_name)
            )
            conn.commit()
            return group_id
        finally:
            conn.close()

    def get_chat_groups(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有对话分组（包含各组下的会话预览）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM chat_groups WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            groups = [dict(row) for row in cursor.fetchall()]

            # 为每个组获取会话
            for group in groups:
                cursor.execute(
                    "SELECT * FROM chat_sessions WHERE group_id = ? ORDER BY updated_at DESC",
                    (group['group_id'],)
                )
                group['sessions'] = [dict(row) for row in cursor.fetchall()]

            return groups
        finally:
            conn.close()

    def update_chat_group(self, group_id: str, user_id: str, name: str) -> bool:
        """更新分组名称"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE chat_groups SET group_name = ? WHERE group_id = ? AND user_id = ?",
                (name, group_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_chat_group(self, group_id: str, user_id: str) -> bool:
        """删除分组"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM chat_groups WHERE group_id = ? AND user_id = ?",
                (group_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def add_chat_session(self, user_id: str, group_id: str, session_name: str, session_id: Optional[str] = None) -> str:
        """创建新的会话"""
        conn = self.get_connection()
        cursor = conn.cursor()
        sid = session_id or str(uuid.uuid4())
        now = datetime.now().isoformat()
        try:
            cursor.execute(
                """INSERT INTO chat_sessions (session_id, group_id, user_id, session_name, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sid, group_id, user_id, session_name, now, now)
            )
            conn.commit()
            return sid
        finally:
            conn.close()

    def update_chat_session(self, session_id: str, user_id: str, name: Optional[str] = None, group_id: Optional[str] = None) -> bool:
        """更新会话信息（重命名或移动分组）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            fields = []
            params = []
            if name:
                fields.append("session_name = ?")
                params.append(name)
            if group_id:
                fields.append("group_id = ?")
                params.append(group_id)

            if not fields: return False

            fields.append("updated_at = ?")
            params.append(datetime.now().isoformat())

            params.extend([session_id, user_id])
            query = f"UPDATE chat_sessions SET {', '.join(fields)} WHERE session_id = ? AND user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_chat_session(self, session_id: str, user_id: str) -> bool:
        """删除会话"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def duplicate_chat_session(self, session_id: str, user_id: str) -> str:
        """克隆并生成一个新的对话会话及其所有消息内容"""
        conn = self.get_connection()
        cursor = conn.cursor()
        new_sid = str(uuid.uuid4())
        now = datetime.now().isoformat()
        try:
            # 1. 获取原会话信息
            cursor.execute("SELECT * FROM chat_sessions WHERE session_id = ? AND user_id = ?", (session_id, user_id))
            old_session = cursor.fetchone()
            if not old_session:
                return None

            # 2. 创建新会话
            cursor.execute(
                """INSERT INTO chat_sessions (session_id, group_id, user_id, session_name, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (new_sid, old_session['group_id'], user_id, f"{old_session['session_name']} (拷贝)", now, now)
            )

            # 3. 复制所有消息
            cursor.execute("SELECT * FROM chat_messages WHERE session_id = ? AND user_id = ? ORDER BY created_at ASC", (session_id, user_id))
            old_messages = cursor.fetchall()

            # 建立 ID 映射以保持回复关系
            id_map = {}
            for msg in old_messages:
                new_msg_id = str(uuid.uuid4())
                id_map[msg['message_id']] = new_msg_id

                # 处理回复引用
                new_reply_to = id_map.get(msg['reply_to_id']) if msg['reply_to_id'] else None

                cursor.execute(
                    """INSERT INTO chat_messages (message_id, session_id, user_id, role, content, tokens, reply_to_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (new_msg_id, new_sid, user_id, msg['role'], msg['content'], msg['tokens'], new_reply_to, msg['created_at'])
                )

            conn.commit()
            return new_sid
        except Exception as e:
            conn.rollback()
            logger.error(f"克隆会话失败: {e}")
            return None
        finally:
            conn.close()

    def add_chat_message(self, user_id: str, session_id: str, role: str, content: str,
                         tokens: int = 0, reply_to_id: Optional[str] = None) -> str:
        """添加新消息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        msg_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        try:
            cursor.execute(
                """INSERT INTO chat_messages (message_id, session_id, user_id, role, content, tokens, reply_to_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (msg_id, session_id, user_id, role, content, tokens, reply_to_id, now)
            )
            # 更新会话的最后活跃时间
            cursor.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )
            conn.commit()
            return msg_id
        finally:
            conn.close()

    def get_chat_messages(self, session_id: str, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取某会话的历史消息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 获取消息并在连接时尝试带上被引用消息的预览
            cursor.execute(
                """SELECT m.*, r.content as reply_content
                   FROM chat_messages m
                   LEFT JOIN chat_messages r ON m.reply_to_id = r.message_id
                   WHERE m.session_id = ? AND m.user_id = ?
                   ORDER BY m.created_at ASC LIMIT ?""",
                (session_id, user_id, limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def clear_chat_history(self, session_id: str, user_id: str) -> bool:
        """清空某会话的历史记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM chat_messages WHERE session_id = ? AND user_id = ?",
                (session_id, user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== 任务链相关方法 ====================
