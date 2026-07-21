"""Layered, explainable personal understanding built from consented first-party signals."""
from __future__ import annotations

from datetime import datetime, timezone
import re
import unicodedata
from typing import Any, Dict, Mapping, Optional, Sequence

from core.personal_context_contracts import PersonalContextError, PersonalContextRepository


PROFILE_DOMAINS = (
    "basic",
    "interests",
    "working_style",
    "communication",
    "values",
    "current_phase",
)
PROFILE_RECORD_STATUSES = {"active", "archived"}
SIGNAL_KINDS = {"favorite", "feedback", "task", "conversation", "import", "manual"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any, *, maximum: int, field: str) -> str:
    text = " ".join(str(value or "").split())
    if not text or len(text) > maximum:
        raise PersonalContextError(f"Invalid {field}.", f"INVALID_{field.upper()}")
    return text


def _profile_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    key = re.sub(r"[^\w.:-]+", "-", normalized, flags=re.UNICODE).strip("-_")
    if not key or len(key) > 160:
        raise PersonalContextError("Invalid profile key.", "INVALID_PROFILE_KEY")
    return key


def _confidence(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise PersonalContextError("Invalid confidence.", "INVALID_PROFILE_CONFIDENCE") from exc
    if not 0 <= result <= 1:
        raise PersonalContextError("Invalid confidence.", "INVALID_PROFILE_CONFIDENCE")
    return round(result, 4)


class ProfileCognition:
    """Own layered profile facts, pending hypotheses, and user feedback.

    Signals are factual and consented. Patterns are deterministic aggregates.
    Hypotheses are always review-required. Facets are the only profile layer that
    can be projected into later AI context.
    """

    def __init__(self, repository: PersonalContextRepository) -> None:
        self._repository = repository

    def create_signal(self, owner_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        """Persist a non-conclusive personal signal owned by one user."""
        return self._repository.create_signal(owner_id, self._normalize_signal(values))

    def upsert_signal(self, owner_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        """Refresh a deterministic signal using a stable source reference."""
        normalized = self._normalize_signal(values)
        if not normalized["source_ref"]:
            raise PersonalContextError(
                "A stable profile signal source is required.", "PROFILE_SIGNAL_SOURCE_REQUIRED"
            )
        return self._repository.upsert_signal(owner_id, normalized)

    def list_signals(
        self, owner_id: str, *, status: Optional[str] = None, limit: int = 100
    ) -> Sequence[Dict[str, Any]]:
        if status is not None and status not in PROFILE_RECORD_STATUSES:
            raise PersonalContextError("Invalid profile signal status.", "INVALID_PROFILE_SIGNAL_STATUS")
        return self._repository.list_signals(owner_id, status=status, limit=limit)

    def sync_memories(self, owner_id: str, memories: Sequence[Mapping[str, Any]]) -> None:
        """Expose explicitly opted-in memories as signals, never inferred facts."""
        for memory in memories:
            memory_id = str(memory.get("memory_id") or "")
            if not memory_id:
                continue
            metadata = memory.get("metadata") if isinstance(memory.get("metadata"), Mapping) else {}
            contributes = (
                metadata.get("contribute_to_profile") is True
                and memory.get("status") == "active"
                and bool(memory.get("use_in_context", True))
            )
            self.upsert_signal(
                owner_id,
                {
                    "kind": "manual",
                    "summary": "一条明确授权的长期记忆可用于理解用户。" if contributes else "一条长期记忆不再用于个人理解。",
                    "source_type": "explicit_memory",
                    "source_ref": f"memory:{memory_id}",
                    "attributes": {
                        "memory_type": str(memory.get("memory_type") or ""),
                        "contributes": contributes,
                    },
                    "weight": 1.0,
                    "observed_at": str(memory.get("updated_at") or _now()),
                    "sensitivity": "private",
                    "status": "active" if contributes else "archived",
                },
            )

    def rebuild_patterns(
        self, owner_id: str, signals: Sequence[Mapping[str, Any]]) -> Sequence[Dict[str, Any]]:
        """Persist deterministic work patterns derived from current aggregate signals."""
        by_ref = {
            str(item.get("source_ref") or ""): item
            for item in signals
            if item.get("status") == "active" and isinstance(item.get("attributes"), Mapping)
        }
        candidates: list[Dict[str, Any]] = []
        reviews = by_ref.get("task_reviews:v1", {}).get("attributes", {})
        if _count(reviews, "review_with_next_action_count") >= 2:
            candidates.append({
                "pattern_key": "reflection-leaves-next-action",
                "label": "近期复盘会记录下一步",
                "detail": f"在已保存的复盘中，有 {_count(reviews, 'review_with_next_action_count')} 次记录了后续行动。",
                "evidence_refs": _signal_ref(by_ref.get("task_reviews:v1")),
                "confidence": 0.78,
            })
        refinements = by_ref.get("goal_refinements:v1", {}).get("attributes", {})
        if _count(refinements, "goal_plan_refinement_count") >= 2:
            candidates.append({
                "pattern_key": "refines-plan-during-work",
                "label": "近期推进中调整过计划",
                "detail": f"已保存 {_count(refinements, 'goal_plan_refinement_count')} 次计划调整记录。",
                "evidence_refs": _signal_ref(by_ref.get("goal_refinements:v1")),
                "confidence": 0.72,
            })
        recovery = by_ref.get("task_recovery:v1", {}).get("attributes", {})
        if _count(recovery, "resume_count") + _count(recovery, "retry_count") >= 2:
            candidates.append({
                "pattern_key": "returns-after-interruption",
                "label": "近期有中断后的恢复记录",
                "detail": f"已保存 {_count(recovery, 'resume_count')} 次恢复和 {_count(recovery, 'retry_count')} 次重试记录。",
                "evidence_refs": _signal_ref(by_ref.get("task_recovery:v1")),
                "confidence": 0.68,
            })
        steps = by_ref.get("task_steps:v1", {}).get("attributes", {})
        if _count(steps, "step_count") >= 6:
            candidates.append({
                "pattern_key": "tracks-work-with-steps",
                "label": "近期计划按步骤跟进",
                "detail": f"当前记录中有 {_count(steps, 'step_count')} 个可追踪的计划步骤。",
                "evidence_refs": _signal_ref(by_ref.get("task_steps:v1")),
                "confidence": 0.74,
            })
        current_keys = {item["pattern_key"] for item in candidates}
        for key in (
            "reflection-leaves-next-action", "refines-plan-during-work",
            "returns-after-interruption", "tracks-work-with-steps",
        ):
            if key not in current_keys:
                self._repository.upsert_pattern(owner_id, {
                    "pattern_key": key, "label": "", "detail": "", "evidence_refs": [],
                    "confidence": 0, "status": "archived", "last_observed_at": _now(),
                })
        for item in candidates:
            item.update({"status": "active", "first_observed_at": None, "last_observed_at": _now()})
            self._repository.upsert_pattern(owner_id, item)
        return self._repository.list_patterns(owner_id, status="active", limit=100)

    def create_hypothesis(self, owner_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        """Create one review-required hypothesis unless the user has closed that key."""
        normalized = self._normalize_hypothesis(values)
        if self._repository.get_suppression(owner_id, normalized["domain"], normalized["profile_key"]):
            raise PersonalContextError(
                "This understanding was previously declined.", "PROFILE_HYPOTHESIS_SUPPRESSED", 409
            )
        facets = self._repository.list_facets(owner_id, status="active", limit=500)
        if any(
            item.get("domain") == normalized["domain"]
            and item.get("profile_key") == normalized["profile_key"]
            for item in facets
        ):
            raise PersonalContextError(
                "This understanding is already confirmed.", "PROFILE_FACET_ALREADY_CONFIRMED", 409
            )
        existing = self._repository.get_hypothesis_by_key(
            owner_id, normalized["domain"], normalized["profile_key"]
        )
        if existing and existing.get("status") == "pending":
            return existing
        return self._repository.create_hypothesis(owner_id, normalized)

    def review_hypothesis(
        self,
        owner_id: str,
        hypothesis_id: str,
        *,
        decision: str,
        value: Any = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Record an explicit user decision and update the canonical layer once."""
        if decision not in {"confirmed", "corrected", "rejected"}:
            raise PersonalContextError("Invalid profile review decision.", "INVALID_PROFILE_REVIEW")
        hypothesis = self._repository.get_hypothesis(owner_id, hypothesis_id)
        if hypothesis is None:
            raise PersonalContextError("Profile hypothesis not found.", "PROFILE_HYPOTHESIS_NOT_FOUND", 404)
        if hypothesis.get("status") != "pending":
            raise PersonalContextError("This understanding has already been reviewed.", "PROFILE_HYPOTHESIS_STATE_CONFLICT", 409)
        if decision == "corrected" and (value is None or not str(value).strip()):
            raise PersonalContextError("A corrected value is required.", "PROFILE_CORRECTION_REQUIRED")
        final_value = value if decision == "corrected" else hypothesis.get("value")
        if not self._repository.update_hypothesis(
            owner_id, hypothesis_id, {"status": decision}
        ):
            raise PersonalContextError("Profile hypothesis changed before review.", "PROFILE_STATE_CONFLICT", 409)
        self._repository.create_feedback(
            owner_id,
            {
                "hypothesis_id": hypothesis_id,
                "domain": hypothesis["domain"],
                "profile_key": hypothesis["profile_key"],
                "decision": decision,
                "value": final_value,
                "reason": str(reason or "").strip()[:500],
            },
        )
        if decision == "rejected":
            self._repository.upsert_suppression(
                owner_id,
                {
                    "domain": hypothesis["domain"],
                    "profile_key": hypothesis["profile_key"],
                    "reason": str(reason or "").strip()[:500],
                    "status": "active",
                },
            )
        else:
            self._repository.archive_suppression(
                owner_id, hypothesis["domain"], hypothesis["profile_key"]
            )
            self._repository.upsert_facet(
                owner_id,
                {
                    "domain": hypothesis["domain"],
                    "profile_key": hypothesis["profile_key"],
                    "label": hypothesis["summary"],
                    "value": final_value,
                    "source": "user_corrected" if decision == "corrected" else "user_confirmed",
                    "source_hypothesis_id": hypothesis_id,
                    "context_enabled": True,
                    "status": "active",
                },
            )
        self.upsert_signal(
            owner_id,
            {
                "kind": "feedback",
                "summary": "用户已审阅一条个人理解。",
                "source_type": "profile_hypothesis_review",
                "source_ref": f"hypothesis:{hypothesis_id}:review",
                "attributes": {"domain": hypothesis["domain"], "decision": decision},
                "weight": 1.0,
                "observed_at": _now(),
                "sensitivity": "private",
                "status": "active",
            },
        )
        return self._repository.get_hypothesis(owner_id, hypothesis_id) or {}

    def view(self, owner_id: str) -> Dict[str, Any]:
        """Return only canonical layered records for a user's profile workspace."""
        signals = self.list_signals(owner_id, status="active", limit=500)
        patterns = self.rebuild_patterns(owner_id, signals)
        return {
            "signals": signals,
            "patterns": patterns,
            "hypotheses": self._repository.list_hypotheses(owner_id, status="pending", limit=200),
            "facets": self._repository.list_facets(owner_id, status="active", limit=200),
        }

    def _normalize_signal(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        kind = str(values.get("kind") or "manual")
        if kind not in SIGNAL_KINDS:
            raise PersonalContextError("Invalid profile signal kind.", "INVALID_PROFILE_SIGNAL_KIND")
        attributes = values.get("attributes") or {}
        if not isinstance(attributes, Mapping):
            raise PersonalContextError("Invalid profile signal attributes.", "INVALID_PROFILE_SIGNAL_ATTRIBUTES")
        status = str(values.get("status") or "active")
        if status not in PROFILE_RECORD_STATUSES:
            raise PersonalContextError("Invalid profile signal status.", "INVALID_PROFILE_SIGNAL_STATUS")
        sensitivity = str(values.get("sensitivity") or "private")
        if sensitivity not in {"personal", "private", "sensitive"}:
            raise PersonalContextError("Invalid profile signal sensitivity.", "INVALID_PROFILE_SIGNAL_SENSITIVITY")
        return {
            "kind": kind,
            "summary": _clean_text(values.get("summary"), maximum=500, field="profile_signal_summary"),
            "source_type": _clean_text(values.get("source_type") or "manual", maximum=60, field="profile_signal_source_type"),
            "source_ref": str(values.get("source_ref") or "").strip()[:500] or None,
            "attributes": dict(attributes),
            "weight": _confidence(values.get("weight", 1.0)),
            "observed_at": str(values.get("observed_at") or "").strip() or _now(),
            "sensitivity": sensitivity,
            "status": status,
        }

    def _normalize_hypothesis(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        domain = str(values.get("domain") or "")
        if domain not in PROFILE_DOMAINS:
            raise PersonalContextError("Invalid profile domain.", "INVALID_PROFILE_DOMAIN")
        evidence = values.get("evidence_refs") or []
        if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
            raise PersonalContextError("Invalid profile evidence references.", "INVALID_PROFILE_EVIDENCE")
        return {
            "domain": domain,
            "profile_key": _profile_key(values.get("profile_key")),
            "value": values.get("value"),
            "summary": _clean_text(values.get("summary"), maximum=240, field="profile_hypothesis_summary"),
            "rationale": str(values.get("rationale") or "").strip()[:1000],
            "confidence": _confidence(values.get("confidence", 0.5)),
            "evidence_refs": list(evidence),
            "status": "pending",
            "first_observed_at": str(values.get("first_observed_at") or "").strip() or None,
            "last_observed_at": str(values.get("last_observed_at") or "").strip() or None,
        }


def _count(values: Mapping[str, Any], key: str) -> int:
    try:
        return max(0, int(values.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def _signal_ref(signal: Mapping[str, Any] | None) -> list[Dict[str, str]]:
    if not signal or not signal.get("signal_id"):
        return []
    return [{"type": "profile_signal", "id": str(signal["signal_id"])}]
