"""
Void System Database Module
----------------------------
提供数据库操作接口，包括用户、属性、任务、系统币等核心功能的数据管理。
"""
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

from adapters.sqlite.migrations import Migration, run_migrations

logger: logging.Logger = logging.getLogger("void-system-db")

class Database:
    def __init__(self, db_path: str = "void_system.db") -> None:
        """
        初始化数据库连接
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn
    
    def _task_workflow_repository(self):
        """Return the focused SQLite Adapter used by Task Workflow."""
        from adapters.sqlite.task_repository import SQLiteTaskRepository

        return SQLiteTaskRepository(self.get_connection)

    def _task_workspace_repository(self):
        """Return the focused SQLite Adapter used by Task Workspace."""
        from adapters.sqlite.task_workspace_repository import SQLiteTaskWorkspaceRepository

        return SQLiteTaskWorkspaceRepository(self.get_connection)

    def test_connection(self) -> None:
        """测试数据库连接"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
    
    def close(self) -> None:
        """关闭数据库连接（如果需要）"""
        pass  # SQLite会自动管理连接
    
    def init_database(self) -> None:
        """Bring the embedded store to the latest ordered schema version."""
        run_migrations(
            self.get_connection,
            [
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
            ],
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
        """Add renewable worker ownership and resumable checkpoints for agent Runs."""
        schema = """
            CREATE TABLE IF NOT EXISTS task_run_leases (
                run_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                worker_id TEXT NOT NULL,
                lease_token TEXT NOT NULL UNIQUE,
                acquired_at TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                checkpoint_data TEXT NOT NULL DEFAULT '{}',
                released_at TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_task_run_leases_expiry
                ON task_run_leases(expires_at, released_at);
            CREATE INDEX IF NOT EXISTS idx_task_run_leases_worker
                ON task_run_leases(worker_id, expires_at);
        """
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)

    def _add_legacy_task_execution_projection(self, conn: sqlite3.Connection) -> None:
        """Link legacy task APIs to the canonical Goal, Run, and Step model."""
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

        from adapters.sqlite.task_execution_projection import backfill_legacy_task_execution

        backfill_legacy_task_execution(conn, datetime.now().isoformat())

    def _add_canonical_reward_settlement_links(self, conn: sqlite3.Connection) -> None:
        """Link legacy reward grants to their canonical Run and Step identities."""
        columns = {
            row[1] for row in conn.execute(
                "PRAGMA table_info(task_reward_settlements)"
            ).fetchall()
        }
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
        """Add indexes used by atomic reward marketplace settlement."""
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_resources_owner_key "
            "ON user_resources(user_id, resource_key)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_coins_user_created_at "
            "ON coins(user_id, created_at)"
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
        """Expose asynchronous planning progress without leaking provider internals."""
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
            experience INTEGER DEFAULT 0,
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
        
        # 任务类别表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_categories (
            category_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            category_name TEXT NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '📚',
            color TEXT DEFAULT '#3B82F6',
            is_preset INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            category_id TEXT,
            chain_id TEXT,
            chain_order INTEGER DEFAULT 0,
            task_name TEXT NOT NULL,
            description TEXT,
            related_attrs TEXT,
            estimated_time INTEGER,
            reward_coins INTEGER DEFAULT 10,
            priority TEXT DEFAULT 'medium',
            attribute_points INTEGER DEFAULT 0,
            completion_type TEXT DEFAULT 'simple',
            completion_criteria TEXT,
            current_progress INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            prerequisites TEXT,  -- JSON 格式存储的前置任务 ID 列表
            task_type TEXT DEFAULT 'main', -- 'main', 'side', 'daily'
            is_optional INTEGER DEFAULT 0, -- 0: 必须, 1: 可选
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            proof_data TEXT,
            self_evaluation TEXT,
            ai_suggestion TEXT,
            is_daily INTEGER DEFAULT 0, -- 0: 否, 1: 是 (映射到每日任务)
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES task_categories(category_id) ON DELETE SET NULL
        )
        ''')

        # 确保旧数据库也有 is_daily 字段
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN is_daily INTEGER DEFAULT 0")
        except:
            pass

        # 任务链表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_chains (
            chain_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            chain_name TEXT NOT NULL,
            description TEXT,
            total_tasks INTEGER DEFAULT 0,
            completed_tasks INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 系统币记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coins (
            record_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # Idempotent task reward ledger. One task can settle rewards only once.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_reward_settlements (
            settlement_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            coins INTEGER NOT NULL DEFAULT 0,
            experience INTEGER NOT NULL DEFAULT 0,
            attribute_increments TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(task_id, user_id),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # 用户资源表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_resources (
            resource_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            resource_key TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 购买记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_history (
            purchase_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            unit_price INTEGER NOT NULL,
            total_price INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')
        
        # 经验值记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experience (
            record_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_coins_user_id ON coins(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_resources_user_id ON user_resources(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_categories_user_id ON task_categories(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchase_user_id ON purchase_history(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_experience_user_id ON experience(user_id)")
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
        
        # 兼容性迁移：为已有数据库添加新字段（忽略已存在的列错误）
        for col, definition in [
            ("priority",             "TEXT DEFAULT 'medium'"),
            ("attribute_points",     "INTEGER DEFAULT 0"),
            ("updated_at",           "TEXT"),
            ("chain_id",             "TEXT"),
            ("chain_order",          "INTEGER DEFAULT 0"),
            ("completion_type",      "TEXT DEFAULT 'simple'"),
            ("completion_criteria",  "TEXT"),
            ("current_progress",     "INTEGER DEFAULT 0"),
            ("prerequisites",        "TEXT"),
            ("task_type",            "TEXT DEFAULT 'main'"),
            ("is_optional",          "INTEGER DEFAULT 0"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col} {definition}")
            except Exception:
                pass
        
        # 确保 updated_at 有值
        try:
            cursor.execute("UPDATE tasks SET updated_at = created_at WHERE updated_at IS NULL")
        except Exception:
            pass
        
        # 兼容性迁移：为 task_chains 表添加外键（如果需要）
        # 注意：SQLite不支持直接ALTER TABLE ADD FOREIGN KEY，通常需要重建表或在创建时就定义
        # 这里假设如果表已存在，外键会在创建时就定义好，或者通过其他方式处理
        # 如果需要添加外键，通常需要更复杂的迁移逻辑，例如：
        # 1. 创建新表，包含外键
        # 2. 从旧表复制数据到新表
        # 3. 删除旧表
        # 4. 重命名新表为旧表名
        # 对于简单的列添加，上述for循环足够。


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
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_tasks_owner_status
               ON tasks(user_id, status, updated_at)"""
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
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 获取总任务数
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,))
            total_tasks = cursor.fetchone()[0]
            
            # 获取已完成任务数
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'completed'", (user_id,))
            completed_tasks = cursor.fetchone()[0]
            
            # 获取进行中任务数
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'in_progress'", (user_id,))
            in_progress_tasks = cursor.fetchone()[0]
            
            # 获取总经验值
            cursor.execute("SELECT SUM(amount) FROM experience WHERE user_id = ?", (user_id,))
            total_exp = cursor.fetchone()[0] or 0
            
            # 获取总获得金币
            cursor.execute("SELECT SUM(amount) FROM coins WHERE user_id = ? AND amount > 0", (user_id,))
            total_earned_coins = cursor.fetchone()[0] or 0
            
            # 获取总消费金币
            cursor.execute("SELECT ABS(SUM(amount)) FROM coins WHERE user_id = ? AND amount < 0", (user_id,))
            total_spent_coins = cursor.fetchone()[0] or 0
            
            # 获取文档总数
            cursor.execute("SELECT COUNT(*) FROM user_documents WHERE user_id = ?", (user_id,))
            doc_count = cursor.fetchone()[0]
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                "total_experience": total_exp,
                "total_earned_coins": total_earned_coins,
                "total_spent_coins": total_spent_coins,
                "total_documents": doc_count
            }
        finally:
            conn.close()
    
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
    
    # ==================== 系统币相关方法 ====================
    def add_coins(self, user_id: str, amount: int, source: str = "task_complete") -> bool:
        """
        增加用户系统币
        Args:
            user_id: 用户ID
            amount: 增加的金额
            source: 来源描述
        Returns:
            是否添加成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        record_id = str(uuid.uuid4())
        try:
            cursor.execute(
                """INSERT INTO coins (record_id, user_id, amount, type, source)
                   VALUES (?, ?, ?, ?, ?)""",
                (record_id, user_id, amount, "earn", source)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def spend_coins(self, user_id: str, amount: int, source: str = "resource_exchange") -> bool:
        """
        扣除用户系统币
        Args:
            user_id: 用户ID
            amount: 扣除的金额
            source: 来源描述
        Returns:
            是否扣除成功（余额不足时返回False）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 先检查余额是否足够
            balance = self.get_user_balance(user_id)
            if balance < amount:
                return False
            
            record_id = str(uuid.uuid4())
            cursor.execute(
                """INSERT INTO coins (record_id, user_id, amount, type, source)
                   VALUES (?, ?, ?, ?, ?)""",
                (record_id, user_id, -amount, "spend", source)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_user_balance(self, user_id: str) -> int:
        """
        获取用户系统币余额
        Args:
            user_id: 用户ID
        Returns:
            用户余额（如果没有记录则返回0）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT SUM(amount) FROM coins WHERE user_id = ?",
                (user_id,)
            )
            balance = cursor.fetchone()[0]
            return balance or 0
        finally:
            conn.close()
    
    def get_coin_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户系统币收支记录
        Args:
            user_id: 用户ID
            limit: 返回记录数量限制
        Returns:
            系统币记录列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT * FROM coins WHERE user_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_income_expense_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户收支统计"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 总收入
            cursor.execute("SELECT SUM(amount) FROM coins WHERE user_id = ? AND amount > 0", (user_id,))
            total_income = cursor.fetchone()[0] or 0
            
            # 总支出
            cursor.execute("SELECT ABS(SUM(amount)) FROM coins WHERE user_id = ? AND amount < 0", (user_id,))
            total_expense = cursor.fetchone()[0] or 0
            
            # 最近7天收入
            cursor.execute("""
                SELECT SUM(amount) FROM coins 
                WHERE user_id = ? AND amount > 0 
                AND created_at >= date('now', '-7 days')
            """, (user_id,))
            weekly_income = cursor.fetchone()[0] or 0
            
            # 最近7天支出
            cursor.execute("""
                SELECT ABS(SUM(amount)) FROM coins 
                WHERE user_id = ? AND amount < 0 
                AND created_at >= date('now', '-7 days')
            """, (user_id,))
            weekly_expense = cursor.fetchone()[0] or 0
            
            return {
                "total_income": total_income,
                "total_expense": total_expense,
                "weekly_income": weekly_income,
                "weekly_expense": weekly_expense,
                "net_income": total_income - total_expense
            }
        finally:
            conn.close()
    
    # ==================== 经验值相关方法 ====================
    def add_experience(self, user_id: str, amount: int, source: str = "task_complete") -> bool:
        """增加用户经验值"""
        conn = self.get_connection()
        cursor = conn.cursor()
        record_id = str(uuid.uuid4())
        try:
            # 添加经验记录
            cursor.execute(
                """INSERT INTO experience (record_id, user_id, amount, source)
                   VALUES (?, ?, ?, ?)""",
                (record_id, user_id, amount, source)
            )
            
            # 更新用户表中的经验值
            cursor.execute(
                "UPDATE users SET experience = experience + ? WHERE user_id = ?",
                (amount, user_id)
            )
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    # ==================== 用户资源相关方法 ====================
    def add_user_resource(self, user_id: str, resource_key: str, quantity: int = 1) -> bool:
        """
        增加用户资源数量
        Args:
            user_id: 用户ID
            resource_key: 资源键名
            quantity: 增加的数量
        Returns:
            是否添加成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 检查资源是否已存在
            cursor.execute(
                """SELECT resource_id, quantity FROM user_resources
                   WHERE user_id = ? AND resource_key = ?""",
                (user_id, resource_key)
            )
            result = cursor.fetchone()
            
            if result:
                # 已存在，更新数量
                new_quantity = result[1] + quantity
                cursor.execute(
                    "UPDATE user_resources SET quantity = ? WHERE resource_id = ?",
                    (new_quantity, result[0])
                )
            else:
                # 不存在，创建新记录
                resource_id = str(uuid.uuid4())
                cursor.execute(
                    """INSERT INTO user_resources
                       (resource_id, user_id, resource_key, quantity)
                       VALUES (?, ?, ?, ?)""",
                    (resource_id, user_id, resource_key, quantity)
                )
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def spend_user_resource(self, user_id: str, resource_key: str, quantity: int = 1) -> bool:
        """
        使用用户资源
        Args:
            user_id: 用户ID
            resource_key: 资源键名
            quantity: 使用的数量
        Returns:
            是否使用成功（资源不足时返回False）
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 检查资源是否足够
            cursor.execute(
                """SELECT resource_id, quantity FROM user_resources
                   WHERE user_id = ? AND resource_key = ?""",
                (user_id, resource_key)
            )
            result = cursor.fetchone()
            
            if not result or result[1] < quantity:
                return False
            
            # 更新数量
            new_quantity = result[1] - quantity
            cursor.execute(
                "UPDATE user_resources SET quantity = ? WHERE resource_id = ?",
                (new_quantity, result[0])
            )
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_user_resources(self, user_id: str) -> Dict[str, int]:
        """
        获取用户资源列表
        Args:
            user_id: 用户ID
        Returns:
            资源键名和数量的字典
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT resource_key, quantity FROM user_resources WHERE user_id = ?",
                (user_id,)
            )
            rows = cursor.fetchall()
            result: Dict[str, int] = {}
            for row in rows:
                result[row[0]] = row[1]
            return result
        finally:
            conn.close()
    
    # ==================== 任务相关方法 ====================
    def add_task(
        self,
        user_id: str,
        task_name: str,
        description: str = "",
        related_attrs: Optional[Dict[str, Any]] = None,
        estimated_time: int = 30,
        reward_coins: int = 10,
        priority: str = "medium",
        attribute_points: int = 0,
        category_id: Optional[str] = None,
        chain_id: Optional[str] = None,
        chain_order: int = 0,
        prerequisites: Optional[List[str]] = None,
        completion_type: str = "simple",
        completion_criteria: Optional[Dict[str, Any]] = None,
        task_type: str = "main",
        is_optional: int = 0,
        is_daily: int = 0,
    ) -> str:
        """Compatibility facade for task creation and canonical execution projection."""
        return self._task_workspace_repository().create_task(
            user_id,
            {
                "task_name": task_name,
                "description": description,
                "related_attrs": related_attrs or {},
                "estimated_time": estimated_time,
                "reward_coins": reward_coins,
                "priority": priority,
                "attribute_points": attribute_points,
                "category_id": category_id,
                "chain_id": chain_id,
                "chain_order": chain_order,
                "prerequisites": prerequisites or [],
                "completion_type": completion_type,
                "completion_criteria": completion_criteria or {},
                "task_type": task_type,
                "is_optional": bool(is_optional),
                "is_daily": bool(is_daily),
            },
        )

    def get_user_tasks(
        self,
        user_id: str,
        task_status: Optional[str] = None,
        category_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户任务列表
        Args:
            user_id: 用户ID
            task_status: 任务状态筛选（可选）
            category_id: 任务类别筛选（可选）
            limit: 返回数量限制（可选）
            offset: 偏移量（可选）
        Returns:
            任务列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM tasks WHERE user_id = ?"
            params: List[Any] = [user_id]
            
            if task_status:
                query += " AND status = ?"
                params.append(task_status)
            
            if category_id:
                query += " AND category_id = ?"
                params.append(category_id)
            
            query += " ORDER BY created_at DESC"
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            if offset is not None and limit is not None:
                query += " OFFSET ?"
                params.append(offset)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            result: List[Dict[str, Any]] = []
            for row in rows:
                task_dict = dict(row)
                # 解析JSON字段，添加错误处理
                try:
                    if task_dict.get("related_attrs"):
                        task_dict["related_attrs"] = json.loads(task_dict["related_attrs"])
                    else:
                        task_dict["related_attrs"] = {}
                except json.JSONDecodeError:
                    task_dict["related_attrs"] = {}
                
                try:
                    if task_dict.get("proof_data"):
                        task_dict["proof_data"] = json.loads(task_dict["proof_data"])
                    else:
                        task_dict["proof_data"] = {}
                except json.JSONDecodeError:
                    task_dict["proof_data"] = {}
                
                try:
                    if task_dict.get("self_evaluation"):
                        task_dict["self_evaluation"] = json.loads(task_dict["self_evaluation"])
                    else:
                        task_dict["self_evaluation"] = {}
                except json.JSONDecodeError:
                    task_dict["self_evaluation"] = {}
                
                try:
                    if task_dict.get("ai_suggestion"):
                        task_dict["ai_suggestion"] = json.loads(task_dict["ai_suggestion"])
                    else:
                        task_dict["ai_suggestion"] = {}
                except json.JSONDecodeError:
                    task_dict["ai_suggestion"] = {}
                
                try:
                    if task_dict.get("prerequisites"):
                        task_dict["prerequisites"] = json.loads(task_dict["prerequisites"])
                    else:
                        task_dict["prerequisites"] = []
                except json.JSONDecodeError:
                    task_dict["prerequisites"] = []
                
                result.append(task_dict)
            
            return result
        finally:
            conn.close()
    
    def update_task_status(self, task_id: str, user_id: str, status: str) -> bool:
        """Compatibility facade for Task Workflow status persistence."""
        return self._task_workflow_repository().update_status(user_id, task_id, status)
    def settle_task_completion(
        self,
        task_id: str,
        user_id: str,
        coins: int,
        experience: int,
        attribute_increments: Dict[str, int],
        source: str,
        ai_suggestion: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Compatibility facade for atomic, idempotent Reward Settlement."""
        from core.task_contracts import RewardGrant

        reward = RewardGrant(
            coins=coins,
            experience=experience,
            attribute_increments=attribute_increments,
            source=source,
        )
        return self._task_workflow_repository().settle_completion(
            user_id,
            task_id,
            reward,
            ai_suggestion=ai_suggestion,
        )
    def submit_task_proof(
        self,
        task_id: str,
        user_id: str,
        proof_data: Dict[str, Any],
    ) -> bool:
        """Compatibility facade for task evidence submission."""
        return self._task_workflow_repository().submit_proof(user_id, task_id, proof_data)
    def update_task_evaluation(
        self,
        task_id: str,
        user_id: str,
        self_evaluation: Optional[Dict[str, Any]] = None,
        ai_suggestion: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Compatibility facade for task evaluation persistence."""
        return self._task_workflow_repository().update_evaluation(
            user_id,
            task_id,
            self_evaluation=self_evaluation,
            ai_suggestion=ai_suggestion,
        )
    def delete_task(self, task_id: str, user_id: str) -> bool:
        """Compatibility facade for owner-scoped task and projection deletion."""
        return self._task_workspace_repository().delete_workspace_task(user_id, task_id)

    def add_task_category(
        self,
        user_id: str,
        category_name: str,
        description: str = "",
        icon: str = "📚",
        color: str = "#3B82F6",
        is_preset: int = 0
    ) -> str:
        """
        添加任务类别
        Args:
            user_id: 用户ID
            category_name: 类别名称
            description: 类别描述
            icon: 类别图标
            color: 类别颜色
            is_preset: 是否为预设类别（0: 自定义, 1: 预设）
        Returns:
            新创建的类别ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        category_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        try:
            cursor.execute(
                """INSERT INTO task_categories
                   (category_id, user_id, category_name, description, icon, color, is_preset, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (category_id, user_id, category_name, description, icon, color, is_preset, now, now)
            )
            conn.commit()
            return category_id
        finally:
            conn.close()
    
    def get_user_task_categories(
        self,
        user_id: str,
        include_preset: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取用户的任务类别列表
        Args:
            user_id: 用户ID
            include_preset: 是否包含预设类别
        Returns:
            任务类别列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if include_preset:
                cursor.execute(
                    """SELECT * FROM task_categories
                       WHERE user_id = ?
                       ORDER BY is_preset DESC, created_at DESC""",
                    (user_id,)
                )
            else:
                cursor.execute(
                    """SELECT * FROM task_categories
                       WHERE user_id = ? AND is_preset = 0
                       ORDER BY created_at DESC""",
                    (user_id,)
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def update_task_category(
        self,
        category_id: str,
        user_id: str,
        category_name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None
    ) -> bool:
        """
        更新任务类别
        Args:
            category_id: 类别ID
            user_id: 用户ID
            category_name: 新的类别名称（可选）
            description: 新的类别描述（可选）
            icon: 新的类别图标（可选）
            color: 新的类别颜色（可选）
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates: List[str] = []
            params: List[Any] = []
            
            if category_name is not None:
                updates.append("category_name = ?")
                params.append(category_name)
            
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if icon is not None:
                updates.append("icon = ?")
                params.append(icon)
            
            if color is not None:
                updates.append("color = ?")
                params.append(color)
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(category_id)
            params.append(user_id)
            
            query = f"UPDATE task_categories SET {', '.join(updates)} WHERE category_id = ? AND user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_task_category(self, category_id: str, user_id: str) -> bool:
        """
        删除任务类别
        Args:
            category_id: 类别ID
            user_id: 用户ID
        Returns:
            是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 只能删除自定义类别，不能删除预设类别
            cursor.execute(
                """DELETE FROM task_categories
                   WHERE category_id = ? AND user_id = ? AND is_preset = 0""",
                (category_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def init_preset_categories(self, user_id: str) -> None:
        """
        初始化预设任务类别
        Args:
            user_id: 用户ID
        """
        preset_categories = [
            ("学习Python数据分析", "学习Python数据分析相关知识和技能", "🐍"),
            ("准备英语四级考试", "英语四级考试备考计划", "📚"),
            ("学习Vue 3框架", "学习Vue 3前端框架", "💻"),
            ("减肥健身计划", "制定并执行减肥健身计划", "🏃‍♂️"),
            ("学习摄影技巧", "学习摄影基础知识和技巧", "📷"),
            ("准备考研数学", "考研数学备考计划", "📐"),
            ("学习UI设计", "学习UI设计相关知识", "🎨"),
            ("学习吉他基础", "学习吉他基础知识和弹奏技巧", "🎸")
        ]
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 检查是否已存在预设类别
            cursor.execute(
                """SELECT COUNT(*) FROM task_categories
                   WHERE user_id = ? AND is_preset = 1""",
                (user_id,)
            )
            if cursor.fetchone()[0] > 0:
                return  # 已存在预设类别，跳过初始化
            
            # 批量插入预设类别
            now = datetime.now().isoformat()
            for category_name, description, icon in preset_categories:
                category_id = str(uuid.uuid4())
                cursor.execute(
                    """INSERT INTO task_categories
                       (category_id, user_id, category_name, description, icon, is_preset, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (category_id, user_id, category_name, description, icon, 1, now, now)
                )
            conn.commit()
        finally:
            conn.close()
    
    # ==================== 兑换中心相关方法 ====================
    def purchase_reward_item(
        self,
        user_id: str,
        item_id: str,
        item_name: str,
        quantity: int,
        unit_price: int,
    ) -> Optional[int]:
        """Settle a reward marketplace purchase in one SQLite transaction.

        Returns the remaining balance, or ``None`` when the user cannot afford the
        purchase. Inventory, ledger activity, and purchase history either all
        commit together or none of them do.
        """
        total_price = quantity * unit_price
        resource_key = f"shop_{item_id}"
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM coins WHERE user_id = ?",
                (user_id,),
            )
            balance = int(cursor.fetchone()[0] or 0)
            if balance < total_price:
                conn.rollback()
                return None

            cursor.execute(
                """INSERT INTO coins (record_id, user_id, amount, type, source)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    user_id,
                    -total_price,
                    "spend",
                    f"reward_marketplace:{item_id}",
                ),
            )
            cursor.execute(
                "SELECT resource_id FROM user_resources WHERE user_id = ? AND resource_key = ?",
                (user_id, resource_key),
            )
            resource = cursor.fetchone()
            if resource:
                cursor.execute(
                    """UPDATE user_resources
                       SET quantity = quantity + ?
                       WHERE resource_id = ?""",
                    (quantity, resource[0]),
                )
            else:
                cursor.execute(
                    """INSERT INTO user_resources
                       (resource_id, user_id, resource_key, quantity)
                       VALUES (?, ?, ?, ?)""",
                    (str(uuid.uuid4()), user_id, resource_key, quantity),
                )
            cursor.execute(
                """INSERT INTO purchase_history
                   (purchase_id, user_id, item_id, item_name, quantity, unit_price, total_price)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    user_id,
                    item_id,
                    item_name,
                    quantity,
                    unit_price,
                    total_price,
                ),
            )
            conn.commit()
            return balance - total_price
        except Exception:
            conn.rollback()
            raise
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

    def create_task_chain(
        self,
        user_id: str,
        chain_name: str,
        description: str = "",
        generation_status: str = "ready",
    ) -> str:
        """Create a workflow container and expose its planning state to the UI."""
        conn = self.get_connection()
        cursor = conn.cursor()
        chain_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        try:
            cursor.execute(
                """INSERT INTO task_chains
                   (chain_id, user_id, chain_name, description, generation_status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (chain_id, user_id, chain_name, description, generation_status, now, now),
            )
            conn.commit()
            return chain_id
        finally:
            conn.close()

    def update_task_chain_generation_state(
        self,
        chain_id: str,
        user_id: str,
        generation_status: str,
        generation_error: Optional[str] = None,
    ) -> bool:
        """Record a user-actionable planning state for an owned workflow."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """UPDATE task_chains
                   SET generation_status = ?, generation_error = ?, updated_at = ?
                   WHERE chain_id = ? AND user_id = ?""",
                (generation_status, generation_error, datetime.now().isoformat(), chain_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def create_task_chain_steps(
        self,
        user_id: str,
        chain_id: str,
        task_specs: List[Dict[str, Any]],
    ) -> List[str]:
        """Compatibility facade for atomically creating projected workflow steps."""
        return self._task_workspace_repository().create_chain_steps(
            user_id, chain_id, task_specs
        )

    def get_user_task_chains(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有任务链（含进度统计）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT tc.*,
                          COUNT(t.task_id) as total_tasks,
                          SUM(CASE WHEN t.status='completed' THEN 1 ELSE 0 END) as completed_tasks
                   FROM task_chains tc
                   LEFT JOIN tasks t ON t.chain_id = tc.chain_id
                   WHERE tc.user_id = ?
                   GROUP BY tc.chain_id
                   ORDER BY tc.created_at DESC""",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_task_chain(self, chain_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取单个任务链详情"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM task_chains WHERE chain_id = ? AND user_id = ?",
                (chain_id, user_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_task_chain(self, chain_id: str, user_id: str) -> bool:
        """Compatibility facade for owner-scoped workflow deletion."""
        return self._task_workspace_repository().delete_chain(user_id, chain_id)

    def add_task_to_chain(self, task_id: str, chain_id: str, chain_order: int) -> bool:
        """Move a compatibility task only after its target canonical Step is durable."""
        from adapters.sqlite.task_execution_projection import (
            append_chain_task_execution,
            create_chain_task_execution,
            delete_task_projection,
            link_legacy_chain_execution,
            link_legacy_task_execution,
            project_chain,
        )

        conn = self.get_connection()
        now = datetime.now().isoformat()
        try:
            conn.execute("BEGIN IMMEDIATE")
            task = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if task is None:
                conn.rollback()
                return False
            task_data = dict(task)
            user_id = str(task_data["user_id"])
            chain = conn.execute(
                "SELECT * FROM task_chains WHERE chain_id = ? AND user_id = ?",
                (chain_id, user_id),
            ).fetchone()
            if chain is None:
                conn.rollback()
                return False
            if task_data.get("chain_id") == chain_id:
                conn.commit()
                return True

            existing_tasks = conn.execute(
                """SELECT * FROM tasks WHERE chain_id = ? AND user_id = ?
                   ORDER BY chain_order, created_at""",
                (chain_id, user_id),
            ).fetchall()
            normalized_order = int(chain_order) if int(chain_order) > 0 else (
                max((int(row["chain_order"] or 0) for row in existing_tasks), default=0) + 1
            )
            prior_task_id = str(existing_tasks[-1]["task_id"]) if existing_tasks else None
            raw_prerequisites = task_data.get("prerequisites")
            try:
                parsed_prerequisites = json.loads(raw_prerequisites) if raw_prerequisites else []
            except (TypeError, json.JSONDecodeError):
                parsed_prerequisites = []
            prerequisites = (
                [str(item) for item in parsed_prerequisites]
                if isinstance(parsed_prerequisites, list) and parsed_prerequisites
                else ([prior_task_id] if prior_task_id else [])
            )
            planned_task = {
                **task_data,
                "chain_id": chain_id,
                "chain_order": normalized_order,
                "prerequisites": prerequisites,
                "created_at": now,
            }
            existing_link = conn.execute(
                """SELECT goal_id, run_id FROM legacy_chain_execution_links
                   WHERE legacy_chain_id = ? AND user_id = ?""",
                (chain_id, user_id),
            ).fetchone()
            if existing_link is None and existing_tasks:
                # Legacy rows may predate the canonical migration; convert them once.
                if project_chain(
                    conn, user_id, dict(chain), [dict(row) for row in existing_tasks], now
                ) is None:
                    raise RuntimeError("Historical task chain migration was not created")
                existing_link = conn.execute(
                    """SELECT goal_id, run_id FROM legacy_chain_execution_links
                       WHERE legacy_chain_id = ? AND user_id = ?""",
                    (chain_id, user_id),
                ).fetchone()

            created_chain_execution = existing_link is None
            if created_chain_execution:
                execution = create_chain_task_execution(
                    conn, user_id, dict(chain), [planned_task], now
                )
            else:
                execution = append_chain_task_execution(
                    conn, user_id, chain_id, [planned_task], now
                )
            if execution is None:
                raise RuntimeError("Moved task canonical execution was not created")

            # The target Step now exists, so the old standalone/chain projection can retire.
            delete_task_projection(conn, user_id, task_id, now)
            cursor = conn.execute(
                """UPDATE tasks SET chain_id = ?, chain_order = ?,
                              prerequisites = ?, updated_at = ?
                   WHERE task_id = ? AND user_id = ?""",
                (
                    chain_id,
                    normalized_order,
                    json.dumps(planned_task["prerequisites"]),
                    now,
                    task_id,
                    user_id,
                ),
            )
            if cursor.rowcount <= 0:
                raise RuntimeError("Task disappeared during workflow move")
            if created_chain_execution:
                link_legacy_chain_execution(conn, user_id, chain_id, execution, now)
            link_legacy_task_execution(
                conn,
                user_id,
                task_id,
                chain_id,
                {
                    "goal_id": str(execution["goal_id"]),
                    "run_id": str(execution["run_id"]),
                    "step_id": str(execution["steps"][task_id]),
                },
                now,
            )
            conn.execute(
                """UPDATE task_chains
                   SET total_tasks = (
                       SELECT COUNT(*) FROM tasks WHERE chain_id = ? AND user_id = ?
                   ), updated_at = ?
                   WHERE chain_id = ? AND user_id = ?""",
                (chain_id, user_id, now, chain_id, user_id),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    # ==================== 任务进度 & 完成配置 ====================

    def update_task_progress(self, task_id: str, user_id: str, progress: int) -> bool:
        """Compatibility facade for task and canonical Step progress."""
        return self._task_workspace_repository().update_task_progress(
            user_id, task_id, progress
        )

    def update_task_completion_config(
        self,
        task_id: str,
        user_id: str,
        completion_type: str,
        completion_criteria: Optional[Dict[str, Any]] = None,
        prerequisites: Optional[List[str]] = None,
    ) -> bool:
        """Update legacy completion settings and the canonical Step contract atomically."""
        from adapters.sqlite.task_execution_projection import ensure_task_projection

        conn = self.get_connection()
        now = datetime.now().isoformat()
        criteria = completion_criteria or {}
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """UPDATE tasks SET completion_type = ?, completion_criteria = ?,
                          prerequisites = ?, updated_at = ?
                   WHERE task_id = ? AND user_id = ?""",
                (
                    completion_type,
                    json.dumps(criteria),
                    json.dumps(prerequisites or []),
                    now,
                    task_id,
                    user_id,
                ),
            )
            if cursor.rowcount > 0:
                link = ensure_task_projection(conn, user_id, task_id, now)
                if link is not None:
                    conn.execute(
                        """UPDATE task_steps SET completion_criteria = ?, updated_at = ?
                           WHERE step_id = ? AND user_id = ?""",
                        (json.dumps(criteria), now, link["step_id"], user_id),
                    )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_ai_evaluation(
        self, task_id: str, user_id: str, ai_result: Dict[str, Any], passed: bool
    ) -> bool:
        """Persist evaluation evidence and request canonical approval atomically."""
        from adapters.sqlite.task_execution_projection import sync_task_status

        conn = self.get_connection()
        now = datetime.now().isoformat()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """UPDATE tasks SET ai_suggestion = ?, proof_data = ?,
                          status = 'pending_evaluation', updated_at = ?
                   WHERE task_id = ? AND user_id = ?""",
                (
                    json.dumps(ai_result),
                    json.dumps({"ai_evaluated": True, "passed": passed, "timestamp": now}),
                    now,
                    task_id,
                    user_id,
                ),
            )
            if cursor.rowcount > 0:
                sync_task_status(conn, user_id, task_id, "pending_evaluation", now)
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
