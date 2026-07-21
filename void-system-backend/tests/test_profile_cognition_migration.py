"""Regression coverage for retiring flat profile cognition tables."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from adapters.sqlite.personal_context_repository import SQLitePersonalContextRepository
from database import Database


class ProfileCognitionMigrationTests(unittest.TestCase):
    """Verify that the layered profile schema fully replaces the former runtime tables."""

    def _connection_factory(self, path: Path):
        def connect() -> sqlite3.Connection:
            connection = sqlite3.connect(path)
            connection.row_factory = sqlite3.Row
            return connection
        return connect

    def test_migrates_legacy_profile_records_without_retaining_live_legacy_tables(self) -> None:
        """Map old observations, claims, and overrides to canonical cognition layers."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "profile-v31.db"
            connect = self._connection_factory(path)
            connection = connect()
            try:
                migrator = Database.__new__(Database)
                migrator._add_profile_cognition(connection)
                now = "2026-07-19T12:00:00+00:00"
                connection.execute(
                    """INSERT INTO profile_observations
                       (observation_id, owner_id, kind, summary, source_type, source_ref, attributes,
                        weight, observed_at, sensitivity, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("signal-owner-a", "owner-a", "task", "安全汇总", "workspace_history_summary",
                     "task_reviews:v1", '{"review_count":4}', 0.8, now, "private", "active", now, now),
                )
                claims = [
                    ("pending", "owner-a", "working_style", "pending-key", "待确认值", "待确认理解", "依据", 0.7, "pending"),
                    ("confirmed", "owner-a", "working_style", "confirmed-key", "确认值", "已确认理解", "依据", 0.8, "confirmed"),
                    ("corrected", "owner-a", "working_style", "corrected-key", "修正值", "已修正理解", "依据", 0.9, "corrected"),
                    ("rejected", "owner-a", "working_style", "rejected-key", "拒绝值", "已拒绝理解", "依据", 0.6, "rejected"),
                    ("other-owner", "owner-b", "working_style", "owner-b-key", "另一位用户", "另一位用户的候选", "依据", 0.6, "pending"),
                ]
                for claim in claims:
                    connection.execute(
                        """INSERT INTO profile_claims
                           (claim_id, owner_id, domain, profile_key, value, summary, rationale, confidence,
                            review_status, evidence_refs, first_observed_at, last_observed_at, status,
                            created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, 'active', ?, ?)""",
                        (*claim, now, now, now, now),
                    )
                overrides = [
                    ("replace-confirmed", "owner-a", "working_style", "confirmed-key", "replace", "覆盖后的值", "", "active", now, now),
                    ("suppress-manual", "owner-a", "working_style", "manual-key", "suppress", None, "用户明确拒绝", "active", now, now),
                ]
                for override in overrides:
                    connection.execute(
                        """INSERT INTO profile_overrides
                           (override_id, owner_id, domain, profile_key, operation, value, reason, status,
                            created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        override,
                    )
                connection.commit()

                migrator._migrate_to_layered_profile_cognition(connection)
                connection.commit()

                tables = {
                    row[0] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                self.assertFalse({"profile_observations", "profile_claims", "profile_overrides"} & tables)
                self.assertTrue({
                    "profile_signals", "profile_patterns", "profile_hypotheses", "profile_facets",
                    "profile_feedback", "profile_suppressions", "profile_legacy_records",
                }.issubset(tables))
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM profile_legacy_records").fetchone()[0], 8
                )
                self.assertEqual(
                    connection.execute("SELECT owner_id FROM profile_signals WHERE signal_id = 'signal-owner-a'").fetchone()[0],
                    "owner-a",
                )
                pending = connection.execute(
                    "SELECT status FROM profile_hypotheses WHERE hypothesis_id = 'pending'"
                ).fetchone()[0]
                archived = connection.execute(
                    "SELECT status FROM profile_hypotheses WHERE hypothesis_id = 'confirmed'"
                ).fetchone()[0]
                self.assertEqual(pending, "archived")
                self.assertEqual(archived, "archived")
                self.assertEqual(
                    connection.execute(
                        "SELECT owner_id FROM profile_hypotheses WHERE hypothesis_id = 'other-owner'"
                    ).fetchone()[0],
                    "owner-b",
                )
            finally:
                connection.close()

            repository = SQLitePersonalContextRepository(connect)
            facets = {item["profile_key"]: item for item in repository.list_facets("owner-a")}
            self.assertEqual(facets["confirmed-key"]["value"], "覆盖后的值")
            self.assertEqual(facets["confirmed-key"]["source"], "user_corrected")
            self.assertEqual(facets["corrected-key"]["value"], "修正值")
            rejected = repository.get_suppression("owner-a", "working_style", "rejected-key")
            manual = repository.get_suppression("owner-a", "working_style", "manual-key")
            self.assertEqual(rejected["status"], "active")
            self.assertEqual(manual["reason"], "用户明确拒绝")
            self.assertEqual(repository.list_hypotheses("owner-b")[0]["profile_key"], "owner-b-key")


    def test_retirement_migration_archives_only_legacy_pending_candidates(self) -> None:
        """Existing databases retain valid new candidates while hiding former claim rows."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "profile-v32.db"
            connect = self._connection_factory(path)
            connection = connect()
            try:
                migrator = Database.__new__(Database)
                migrator._add_profile_cognition(connection)
                migrator._migrate_to_layered_profile_cognition(connection)
                now = "2026-07-20T09:00:00+00:00"
                connection.executemany(
                    """INSERT INTO profile_hypotheses
                       (hypothesis_id, owner_id, domain, profile_key, value, summary, rationale,
                        confidence, evidence_refs, status, created_at, updated_at)
                       VALUES (?, 'owner-a', 'working_style', ?, '', ?, ?, 0.8, '[]', 'pending', ?, ?)""",
                    [
                        ("former-claim", "former-claim", "历史候选", "不应继续作为待确认建议", now, now),
                        ("modern-candidate", "modern-candidate", "新的协作建议", "可以由用户确认或修正", now, now),
                    ],
                )
                connection.execute(
                    """INSERT INTO profile_legacy_records
                       (legacy_record_id, owner_id, record_type, legacy_id, payload, migrated_at)
                       VALUES ('legacy:claim:former-claim', 'owner-a', 'claim', 'former-claim', '{}', ?)""",
                    (now,),
                )
                connection.execute(
                    """INSERT INTO profile_facets
                       (facet_id, owner_id, domain, profile_key, label, value, source,
                        context_enabled, status, created_at, updated_at)
                       VALUES ('facet:override', 'owner-a', 'working_style', 'override',
                               '你修正过的理解', '先说明整体方案。', 'user_corrected', 1, 'active', ?, ?)""",
                    (now, now),
                )
                migrator._retire_legacy_profile_candidates(connection)
                connection.commit()

                statuses = dict(connection.execute(
                    "SELECT hypothesis_id, status FROM profile_hypotheses"
                ).fetchall())
                self.assertEqual(statuses["former-claim"], "archived")
                self.assertEqual(statuses["modern-candidate"], "pending")
                label = connection.execute(
                    "SELECT label FROM profile_facets WHERE facet_id = 'facet:override'"
                ).fetchone()[0]
                self.assertEqual(label, "已修正的协作偏好")
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
