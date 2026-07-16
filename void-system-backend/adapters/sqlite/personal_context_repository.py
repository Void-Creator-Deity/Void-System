"""SQLite adapter for companion settings, memories, profile cognition, and audit."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from adapters.sqlite.task_repository import ConnectionFactory
from core.personal_context_contracts import PersonalContextRepository


_JSON_DEFAULTS = {
    "permissions": {},
    "metadata": {},
    "requested_sections": [],
    "included_sections": [],
    "source_decisions": [],
    "selected_references": [],
    "omitted_sections": [],
    "attributes": {},
    "value": None,
    "evidence_refs": [],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(row: Any) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    item = dict(row)
    for field, default in _JSON_DEFAULTS.items():
        if field not in item:
            continue
        try:
            item[field] = json.loads(item[field]) if item[field] not in (None, "") else default
        except (TypeError, json.JSONDecodeError):
            item[field] = default
    if "enabled" in item:
        item["enabled"] = bool(item["enabled"])
    if "use_in_context" in item:
        item["use_in_context"] = bool(item["use_in_context"])
    return item


class SQLitePersonalContextRepository(PersonalContextRepository):
    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def get_settings(self, owner_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(
                conn.execute(
                    "SELECT * FROM companion_settings WHERE owner_id = ?", (owner_id,)
                ).fetchone()
            )
        finally:
            conn.close()

    def upsert_settings(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO companion_settings
                   (owner_id, enabled, tone, initiative, permissions, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(owner_id) DO UPDATE SET
                       enabled = excluded.enabled,
                       tone = excluded.tone,
                       initiative = excluded.initiative,
                       permissions = excluded.permissions,
                       updated_at = excluded.updated_at""",
                (
                    owner_id,
                    int(bool(values["enabled"])),
                    str(values["tone"]),
                    str(values["initiative"]),
                    _json(values["permissions"]),
                    now,
                    now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    "SELECT * FROM companion_settings WHERE owner_id = ?", (owner_id,)
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def create_memory(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        memory_id = str(uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO personal_memories
                   (memory_id, owner_id, memory_type, title, content, source_type,
                    source_ref, confidence, use_in_context, status, review_status,
                    evidence_refs, review_note, reviewed_at, expires_at, metadata,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    memory_id,
                    owner_id,
                    str(values["memory_type"]),
                    str(values["title"]),
                    str(values["content"]),
                    str(values["source_type"]),
                    values.get("source_ref"),
                    float(values["confidence"]),
                    int(bool(values["use_in_context"])),
                    str(values["status"]),
                    str(values["review_status"]),
                    _json(values.get("evidence_refs", [])),
                    str(values.get("review_note") or ""),
                    values.get("reviewed_at"),
                    values.get("expires_at"),
                    _json(values["metadata"]),
                    now,
                    now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    "SELECT * FROM personal_memories WHERE memory_id = ? AND owner_id = ?",
                    (memory_id, owner_id),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def list_memories(
        self,
        owner_id: str,
        *,
        memory_type: Optional[str] = None,
        status: Optional[str] = None,
        review_status: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[Dict[str, Any]]:
        clauses = ["owner_id = ?"]
        params: list[Any] = [owner_id]
        if memory_type:
            clauses.append("memory_type = ?")
            params.append(memory_type)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if review_status:
            clauses.append("review_status = ?")
            params.append(review_status)
        params.append(limit)
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM personal_memories WHERE "
                + " AND ".join(clauses)
                + " ORDER BY updated_at DESC LIMIT ?",
                params,
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def get_memory(self, owner_id: str, memory_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(
                conn.execute(
                    "SELECT * FROM personal_memories WHERE memory_id = ? AND owner_id = ?",
                    (memory_id, owner_id),
                ).fetchone()
            )
        finally:
            conn.close()

    def find_memory_by_source(
        self, owner_id: str, source_type: str, source_ref: str
    ) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(conn.execute(
                """SELECT * FROM personal_memories
                   WHERE owner_id = ? AND source_type = ? AND source_ref = ?
                   ORDER BY updated_at DESC LIMIT 1""",
                (owner_id, source_type, source_ref),
            ).fetchone())
        finally:
            conn.close()

    def update_memory(
        self, owner_id: str, memory_id: str, values: Mapping[str, Any]
    ) -> bool:
        allowed = {
            "memory_type", "title", "content", "source_type", "source_ref",
            "confidence", "use_in_context", "status", "review_status",
            "evidence_refs", "review_note", "reviewed_at", "expires_at", "metadata",
        }
        fields = [field for field in allowed if field in values]
        if not fields:
            return False
        assignments = [f"{field} = ?" for field in fields]
        params: list[Any] = []
        for field in fields:
            value = values[field]
            if field in {"metadata", "evidence_refs"}:
                value = _json(value)
            elif field == "use_in_context":
                value = int(bool(value))
            params.append(value)
        assignments.append("updated_at = ?")
        params.extend((_now(), memory_id, owner_id))
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                f"UPDATE personal_memories SET {', '.join(assignments)} "
                "WHERE memory_id = ? AND owner_id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_memory(self, owner_id: str, memory_id: str) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                "DELETE FROM personal_memories WHERE memory_id = ? AND owner_id = ?",
                (memory_id, owner_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def create_observation(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        observation_id = str(uuid.uuid4())
        now = _now()
        observed_at = values.get("observed_at") or now
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO profile_observations
                   (observation_id, owner_id, kind, summary, source_type, source_ref,
                    attributes, weight, observed_at, sensitivity, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    observation_id, owner_id, values["kind"], values["summary"],
                    values["source_type"], values.get("source_ref"),
                    _json(values["attributes"]), float(values["weight"]), observed_at,
                    values["sensitivity"], values["status"], now, now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    "SELECT * FROM profile_observations WHERE observation_id = ? AND owner_id = ?",
                    (observation_id, owner_id),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def upsert_observation(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        source_ref = values.get("source_ref")
        if not source_ref:
            raise ValueError("source_ref is required for observation upsert")
        now = _now()
        observed_at = values.get("observed_at") or now
        conn = self._connection_factory()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                """SELECT observation_id FROM profile_observations
                   WHERE owner_id = ? AND source_type = ? AND source_ref = ?
                   ORDER BY updated_at DESC, created_at DESC LIMIT 1""",
                (owner_id, values["source_type"], source_ref),
            ).fetchone()
            if existing is None:
                observation_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO profile_observations
                       (observation_id, owner_id, kind, summary, source_type, source_ref,
                        attributes, weight, observed_at, sensitivity, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        observation_id, owner_id, values["kind"], values["summary"],
                        values["source_type"], source_ref, _json(values["attributes"]),
                        float(values["weight"]), observed_at, values["sensitivity"],
                        values["status"], now, now,
                    ),
                )
            else:
                observation_id = existing["observation_id"]
                conn.execute(
                    """UPDATE profile_observations
                       SET kind = ?, summary = ?, attributes = ?, weight = ?, observed_at = ?,
                           sensitivity = ?, status = ?, updated_at = ?
                       WHERE observation_id = ? AND owner_id = ?""",
                    (
                        values["kind"], values["summary"], _json(values["attributes"]),
                        float(values["weight"]), observed_at, values["sensitivity"],
                        values["status"], now, observation_id, owner_id,
                    ),
                )
            conn.commit()
            return _decode(
                conn.execute(
                    "SELECT * FROM profile_observations WHERE observation_id = ? AND owner_id = ?",
                    (observation_id, owner_id),
                ).fetchone()
            ) or {}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def list_observations(
        self, owner_id: str, *, status: Optional[str] = None, limit: int = 100
    ) -> Sequence[Dict[str, Any]]:
        clauses = ["owner_id = ?"]
        params: list[Any] = [owner_id]
        if status:
            clauses.append("status = ?")
            params.append(status)
        params.append(limit)
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM profile_observations WHERE "
                + " AND ".join(clauses)
                + " ORDER BY observed_at DESC, created_at DESC LIMIT ?",
                params,
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def upsert_claim(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        claim_id = str(uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO profile_claims
                   (claim_id, owner_id, domain, profile_key, value, summary, rationale,
                    confidence, review_status, evidence_refs, first_observed_at,
                    last_observed_at, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(owner_id, domain, profile_key) DO UPDATE SET
                       value = excluded.value,
                       summary = excluded.summary,
                       rationale = excluded.rationale,
                       confidence = excluded.confidence,
                       review_status = CASE
                           WHEN profile_claims.review_status IN ('confirmed', 'corrected', 'rejected')
                           THEN profile_claims.review_status
                           ELSE excluded.review_status
                       END,
                       evidence_refs = excluded.evidence_refs,
                       first_observed_at = COALESCE(profile_claims.first_observed_at, excluded.first_observed_at),
                       last_observed_at = excluded.last_observed_at,
                       status = excluded.status,
                       updated_at = excluded.updated_at""",
                (
                    claim_id, owner_id, values["domain"], values["profile_key"],
                    _json(values.get("value")), values["summary"], values.get("rationale", ""),
                    float(values["confidence"]), values["review_status"],
                    _json(values.get("evidence_refs", [])), values.get("first_observed_at"),
                    values.get("last_observed_at"), values["status"], now, now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    """SELECT * FROM profile_claims
                       WHERE owner_id = ? AND domain = ? AND profile_key = ?""",
                    (owner_id, values["domain"], values["profile_key"]),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def create_claim(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        return self.upsert_claim(owner_id, values)

    def list_claims(
        self, owner_id: str, *, status: Optional[str] = None, limit: int = 200
    ) -> Sequence[Dict[str, Any]]:
        clauses = ["owner_id = ?"]
        params: list[Any] = [owner_id]
        if status:
            clauses.append("status = ?")
            params.append(status)
        params.append(limit)
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM profile_claims WHERE "
                + " AND ".join(clauses)
                + " ORDER BY updated_at DESC LIMIT ?",
                params,
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def get_claim(self, owner_id: str, claim_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(
                conn.execute(
                    "SELECT * FROM profile_claims WHERE claim_id = ? AND owner_id = ?",
                    (claim_id, owner_id),
                ).fetchone()
            )
        finally:
            conn.close()

    def update_claim(
        self, owner_id: str, claim_id: str, values: Mapping[str, Any]
    ) -> bool:
        allowed = {
            "value", "summary", "rationale", "confidence", "review_status",
            "evidence_refs", "first_observed_at", "last_observed_at", "status",
        }
        fields = [field for field in allowed if field in values]
        if not fields:
            return False
        assignments = [f"{field} = ?" for field in fields]
        params: list[Any] = []
        for field in fields:
            value = values[field]
            if field in {"value", "evidence_refs"}:
                value = _json(value)
            params.append(value)
        assignments.append("updated_at = ?")
        params.extend((_now(), claim_id, owner_id))
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                f"UPDATE profile_claims SET {', '.join(assignments)} "
                "WHERE claim_id = ? AND owner_id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def upsert_override(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        override_id = str(uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO profile_overrides
                   (override_id, owner_id, domain, profile_key, operation, value,
                    reason, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(owner_id, domain, profile_key) DO UPDATE SET
                       operation = excluded.operation,
                       value = excluded.value,
                       reason = excluded.reason,
                       status = excluded.status,
                       updated_at = excluded.updated_at""",
                (
                    override_id, owner_id, values["domain"], values["profile_key"],
                    values["operation"], _json(values.get("value")),
                    values.get("reason", ""), values["status"], now, now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    """SELECT * FROM profile_overrides
                       WHERE owner_id = ? AND domain = ? AND profile_key = ?""",
                    (owner_id, values["domain"], values["profile_key"]),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def list_overrides(
        self, owner_id: str, *, status: Optional[str] = None
    ) -> Sequence[Dict[str, Any]]:
        clauses = ["owner_id = ?"]
        params: list[Any] = [owner_id]
        if status:
            clauses.append("status = ?")
            params.append(status)
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                "SELECT * FROM profile_overrides WHERE "
                + " AND ".join(clauses)
                + " ORDER BY updated_at DESC",
                params,
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def archive_override(self, owner_id: str, domain: str, profile_key: str) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                """UPDATE profile_overrides SET status = 'archived', updated_at = ?
                   WHERE owner_id = ? AND domain = ? AND profile_key = ? AND status = 'active'""",
                (_now(), owner_id, domain, profile_key),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def record_access(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        audit_id = str(uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO context_access_audit
                   (audit_id, owner_id, purpose, requested_sections,
                    included_sections, item_count, source_decisions,
                    selected_references, omitted_sections, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    audit_id,
                    owner_id,
                    str(values["purpose"]),
                    _json(values["requested_sections"]),
                    _json(values["included_sections"]),
                    int(values["item_count"]),
                    _json(values.get("source_decisions", [])),
                    _json(values.get("selected_references", [])),
                    _json(values.get("omitted_sections", [])),
                    now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    "SELECT * FROM context_access_audit WHERE audit_id = ?", (audit_id,)
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def list_access_log(
        self, owner_id: str, limit: int = 50
    ) -> Sequence[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            rows = conn.execute(
                """SELECT * FROM context_access_audit
                   WHERE owner_id = ? ORDER BY created_at DESC LIMIT ?""",
                (owner_id, limit),
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()
