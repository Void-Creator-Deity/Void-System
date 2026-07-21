"""SQLite adapter for companion settings, memories, profile cognition, and audit."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from adapters.sqlite.connection import ConnectionFactory
from core.personal_context_contracts import PersonalContextRepository


_JSON_DEFAULTS = {
    "permissions": {},
    "persona": {},
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
        raw_value = item[field]
        if raw_value in (None, ""):
            item[field] = default
            continue
        try:
            item[field] = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            # Early profile rows stored human-readable scalar values directly.
            # Keep those values intact while structured fields still fall back
            # to their documented empty defaults.
            item[field] = raw_value if field == "value" else default
    if "enabled" in item:
        item["enabled"] = bool(item["enabled"])
    if "use_in_context" in item:
        item["use_in_context"] = bool(item["use_in_context"])
    if "context_enabled" in item:
        item["context_enabled"] = bool(item["context_enabled"])
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
                   (owner_id, enabled, tone, initiative, persona, permissions, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(owner_id) DO UPDATE SET
                       enabled = excluded.enabled,
                       tone = excluded.tone,
                       initiative = excluded.initiative,
                       persona = excluded.persona,
                       permissions = excluded.permissions,
                       updated_at = excluded.updated_at""",
                (
                    owner_id,
                    int(bool(values["enabled"])),
                    str(values["tone"]),
                    str(values["initiative"]),
                    _json(values["persona"]),
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

    def create_signal(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Persist one user-authorized, traceable signal without inferring a conclusion."""
        signal_id = str(uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO profile_signals
                   (signal_id, owner_id, kind, summary, source_type, source_ref, attributes,
                    weight, observed_at, sensitivity, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    signal_id, owner_id, values["kind"], values["summary"],
                    values["source_type"], values.get("source_ref"), _json(values["attributes"]),
                    float(values["weight"]), values["observed_at"], values["sensitivity"],
                    values["status"], now, now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    "SELECT * FROM profile_signals WHERE signal_id = ? AND owner_id = ?",
                    (signal_id, owner_id),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def upsert_signal(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Refresh a deterministic signal using its stable source reference."""
        source_ref = str(values["source_ref"])
        now = _now()
        conn = self._connection_factory()
        try:
            row = conn.execute(
                """SELECT signal_id FROM profile_signals
                   WHERE owner_id = ? AND source_type = ? AND source_ref = ?""",
                (owner_id, values["source_type"], source_ref),
            ).fetchone()
            if row is None:
                signal_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO profile_signals
                       (signal_id, owner_id, kind, summary, source_type, source_ref, attributes,
                        weight, observed_at, sensitivity, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        signal_id, owner_id, values["kind"], values["summary"],
                        values["source_type"], source_ref, _json(values["attributes"]),
                        float(values["weight"]), values["observed_at"], values["sensitivity"],
                        values["status"], now, now,
                    ),
                )
            else:
                signal_id = str(row["signal_id"])
                conn.execute(
                    """UPDATE profile_signals
                       SET kind = ?, summary = ?, attributes = ?, weight = ?, observed_at = ?,
                           sensitivity = ?, status = ?, updated_at = ?
                       WHERE signal_id = ? AND owner_id = ?""",
                    (
                        values["kind"], values["summary"], _json(values["attributes"]),
                        float(values["weight"]), values["observed_at"], values["sensitivity"],
                        values["status"], now, signal_id, owner_id,
                    ),
                )
            conn.commit()
            return _decode(
                conn.execute(
                    "SELECT * FROM profile_signals WHERE signal_id = ? AND owner_id = ?",
                    (signal_id, owner_id),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def list_signals(
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
                "SELECT * FROM profile_signals WHERE " + " AND ".join(clauses)
                + " ORDER BY observed_at DESC, updated_at DESC LIMIT ?",
                params,
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def upsert_pattern(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        pattern_id = str(values.get("pattern_id") or uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO profile_patterns
                   (pattern_id, owner_id, pattern_key, label, detail, evidence_refs, confidence,
                    status, first_observed_at, last_observed_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(owner_id, pattern_key) DO UPDATE SET
                       label = excluded.label, detail = excluded.detail,
                       evidence_refs = excluded.evidence_refs, confidence = excluded.confidence,
                       status = excluded.status, last_observed_at = excluded.last_observed_at,
                       updated_at = excluded.updated_at""",
                (
                    pattern_id, owner_id, values["pattern_key"], values["label"], values["detail"],
                    _json(values.get("evidence_refs", [])), float(values.get("confidence", 0.5)),
                    values.get("status", "active"), values.get("first_observed_at"),
                    values.get("last_observed_at"), now, now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    """SELECT * FROM profile_patterns
                       WHERE owner_id = ? AND pattern_key = ?""",
                    (owner_id, values["pattern_key"]),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def list_patterns(
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
                "SELECT * FROM profile_patterns WHERE " + " AND ".join(clauses)
                + " ORDER BY updated_at DESC LIMIT ?",
                params,
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def create_hypothesis(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Create a pending hypothesis or reopen only its archived predecessor.

        Input: a normalized key unique to one owner.
        Output: the new or reopened pending record.
        Called by: ProfileCognition after suppression and confirmed-facet checks.
        """
        hypothesis_id = str(uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            existing = conn.execute(
                """SELECT hypothesis_id, status FROM profile_hypotheses
                   WHERE owner_id = ? AND domain = ? AND profile_key = ?""",
                (owner_id, values["domain"], values["profile_key"]),
            ).fetchone()
            if existing is not None:
                if str(existing["status"]) != "archived":
                    raise ValueError("profile hypothesis key is already active or reviewed")
                hypothesis_id = str(existing["hypothesis_id"])
                conn.execute(
                    """UPDATE profile_hypotheses
                       SET value = ?, summary = ?, rationale = ?, confidence = ?, evidence_refs = ?,
                           status = 'pending', first_observed_at = ?, last_observed_at = ?, updated_at = ?
                       WHERE hypothesis_id = ? AND owner_id = ?""",
                    (
                        _json(values.get("value")), values["summary"], values.get("rationale", ""),
                        float(values["confidence"]), _json(values.get("evidence_refs", [])),
                        values.get("first_observed_at"), values.get("last_observed_at"), now,
                        hypothesis_id, owner_id,
                    ),
                )
            else:
                conn.execute(
                    """INSERT INTO profile_hypotheses
                       (hypothesis_id, owner_id, domain, profile_key, value, summary, rationale,
                        confidence, evidence_refs, status, first_observed_at, last_observed_at,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        hypothesis_id, owner_id, values["domain"], values["profile_key"],
                        _json(values.get("value")), values["summary"], values.get("rationale", ""),
                        float(values["confidence"]), _json(values.get("evidence_refs", [])),
                        values.get("status", "pending"), values.get("first_observed_at"),
                        values.get("last_observed_at"), now, now,
                    ),
                )
            conn.commit()
            return _decode(
                conn.execute(
                    "SELECT * FROM profile_hypotheses WHERE hypothesis_id = ? AND owner_id = ?",
                    (hypothesis_id, owner_id),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def list_hypotheses(
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
                "SELECT * FROM profile_hypotheses WHERE " + " AND ".join(clauses)
                + " ORDER BY updated_at DESC LIMIT ?",
                params,
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def get_hypothesis(self, owner_id: str, hypothesis_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(
                conn.execute(
                    """SELECT * FROM profile_hypotheses
                       WHERE hypothesis_id = ? AND owner_id = ?""",
                    (hypothesis_id, owner_id),
                ).fetchone()
            )
        finally:
            conn.close()

    def get_hypothesis_by_key(
        self, owner_id: str, domain: str, profile_key: str
    ) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(
                conn.execute(
                    """SELECT * FROM profile_hypotheses
                       WHERE owner_id = ? AND domain = ? AND profile_key = ?""",
                    (owner_id, domain, profile_key),
                ).fetchone()
            )
        finally:
            conn.close()

    def update_hypothesis(
        self, owner_id: str, hypothesis_id: str, values: Mapping[str, Any]
    ) -> bool:
        allowed = {"status", "value", "summary", "rationale", "confidence", "evidence_refs"}
        assignments: list[str] = []
        params: list[Any] = []
        for key in allowed:
            if key not in values:
                continue
            assignments.append(f"{key} = ?")
            if key in {"value", "evidence_refs"}:
                params.append(_json(values[key]))
            else:
                params.append(values[key])
        if not assignments:
            return False
        assignments.append("updated_at = ?")
        params.extend((_now(), hypothesis_id, owner_id))
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                f"UPDATE profile_hypotheses SET {', '.join(assignments)} "
                "WHERE hypothesis_id = ? AND owner_id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def upsert_facet(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        facet_id = str(values.get("facet_id") or uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO profile_facets
                   (facet_id, owner_id, domain, profile_key, label, value, source,
                    source_hypothesis_id, context_enabled, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(owner_id, domain, profile_key) DO UPDATE SET
                       label = excluded.label, value = excluded.value, source = excluded.source,
                       source_hypothesis_id = excluded.source_hypothesis_id,
                       context_enabled = excluded.context_enabled, status = excluded.status,
                       updated_at = excluded.updated_at""",
                (
                    facet_id, owner_id, values["domain"], values["profile_key"], values["label"],
                    _json(values.get("value")), values["source"], values.get("source_hypothesis_id"),
                    int(bool(values.get("context_enabled", True))), values.get("status", "active"), now, now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    """SELECT * FROM profile_facets
                       WHERE owner_id = ? AND domain = ? AND profile_key = ?""",
                    (owner_id, values["domain"], values["profile_key"]),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def list_facets(
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
                "SELECT * FROM profile_facets WHERE " + " AND ".join(clauses)
                + " ORDER BY updated_at DESC LIMIT ?",
                params,
            ).fetchall()
            return [_decode(row) or {} for row in rows]
        finally:
            conn.close()

    def create_feedback(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        feedback_id = str(uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO profile_feedback
                   (feedback_id, owner_id, hypothesis_id, domain, profile_key, decision,
                    value, reason, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    feedback_id, owner_id, values.get("hypothesis_id"), values["domain"],
                    values["profile_key"], values["decision"], _json(values.get("value")),
                    values.get("reason", ""), now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    "SELECT * FROM profile_feedback WHERE feedback_id = ?",
                    (feedback_id,),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def upsert_suppression(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        suppression_id = str(values.get("suppression_id") or uuid.uuid4())
        now = _now()
        conn = self._connection_factory()
        try:
            conn.execute(
                """INSERT INTO profile_suppressions
                   (suppression_id, owner_id, domain, profile_key, reason, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(owner_id, domain, profile_key) DO UPDATE SET
                       reason = excluded.reason, status = excluded.status, updated_at = excluded.updated_at""",
                (
                    suppression_id, owner_id, values["domain"], values["profile_key"],
                    values.get("reason", ""), values.get("status", "active"), now, now,
                ),
            )
            conn.commit()
            return _decode(
                conn.execute(
                    """SELECT * FROM profile_suppressions
                       WHERE owner_id = ? AND domain = ? AND profile_key = ?""",
                    (owner_id, values["domain"], values["profile_key"]),
                ).fetchone()
            ) or {}
        finally:
            conn.close()

    def get_suppression(
        self, owner_id: str, domain: str, profile_key: str
    ) -> Optional[Dict[str, Any]]:
        conn = self._connection_factory()
        try:
            return _decode(
                conn.execute(
                    """SELECT * FROM profile_suppressions
                       WHERE owner_id = ? AND domain = ? AND profile_key = ? AND status = 'active'""",
                    (owner_id, domain, profile_key),
                ).fetchone()
            )
        finally:
            conn.close()

    def archive_suppression(self, owner_id: str, domain: str, profile_key: str) -> bool:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                """UPDATE profile_suppressions SET status = 'archived', updated_at = ?
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
