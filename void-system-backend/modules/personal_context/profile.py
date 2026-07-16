"""Explainable profile cognition built from evidence, claims, and user overrides."""
from __future__ import annotations

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
CLAIM_REVIEW_STATUSES = {"pending", "confirmed", "rejected", "corrected"}
PROFILE_RECORD_STATUSES = {"active", "archived"}
OBSERVATION_KINDS = {"favorite", "feedback", "task", "conversation", "import", "manual"}
OVERRIDE_OPERATIONS = {"replace", "suppress"}

_MEMORY_DOMAIN = {
    "fact": "basic",
    "preference": "interests",
    "inference": "working_style",
}


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
    """Own raw claims, user corrections, and the effective profile view."""

    def __init__(self, repository: PersonalContextRepository) -> None:
        self._repository = repository

    def create_observation(self, owner_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        return self._repository.create_observation(owner_id, self._normalize_observation(values))

    def upsert_observation(self, owner_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_observation(values)
        if not normalized["source_ref"]:
            raise PersonalContextError(
                "A stable observation source reference is required.",
                "OBSERVATION_SOURCE_REF_REQUIRED",
            )
        return self._repository.upsert_observation(owner_id, normalized)

    def _normalize_observation(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        kind = str(values.get("kind") or "manual")
        if kind not in OBSERVATION_KINDS:
            raise PersonalContextError("Invalid observation kind.", "INVALID_OBSERVATION_KIND")
        attributes = values.get("attributes") or {}
        if not isinstance(attributes, Mapping):
            raise PersonalContextError("Invalid observation attributes.", "INVALID_OBSERVATION_ATTRIBUTES")
        status = str(values.get("status") or "active")
        if status not in PROFILE_RECORD_STATUSES:
            raise PersonalContextError("Invalid observation status.", "INVALID_OBSERVATION_STATUS")
        sensitivity = str(values.get("sensitivity") or "private")
        if sensitivity not in {"personal", "private", "sensitive"}:
            raise PersonalContextError("Invalid observation sensitivity.", "INVALID_OBSERVATION_SENSITIVITY")
        return {
            "kind": kind,
            "summary": _clean_text(values.get("summary"), maximum=500, field="observation_summary"),
            "source_type": _clean_text(values.get("source_type") or "manual", maximum=60, field="observation_source_type"),
            "source_ref": str(values.get("source_ref") or "").strip()[:500] or None,
            "attributes": dict(attributes),
            "weight": _confidence(values.get("weight", 1.0)),
            "observed_at": str(values.get("observed_at") or "").strip() or None,
            "sensitivity": sensitivity,
            "status": status,
        }

    def list_observations(self, owner_id: str, *, status: Optional[str] = None, limit: int = 100) -> Sequence[Dict[str, Any]]:
        if status is not None and status not in PROFILE_RECORD_STATUSES:
            raise PersonalContextError("Invalid observation status.", "INVALID_OBSERVATION_STATUS")
        return self._repository.list_observations(owner_id, status=status, limit=limit)

    def create_claim(self, owner_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_claim(values)
        return self._repository.create_claim(owner_id, normalized)

    def sync_memories(self, owner_id: str, memories: Sequence[Mapping[str, Any]]) -> None:
        for memory in memories:
            memory_id = str(memory.get("memory_id") or "")
            if not memory_id:
                continue
            metadata = memory.get("metadata") if isinstance(memory.get("metadata"), Mapping) else {}
            if metadata.get("contribute_to_profile") is not True:
                self._archive_memory_claims(owner_id, memory_id)
                continue
            memory_type = str(memory.get("memory_type") or "")
            default_domain = _MEMORY_DOMAIN.get(memory_type)
            if default_domain is None:
                self._archive_memory_claims(owner_id, memory_id)
                continue
            requested_domain = str(metadata.get("profile_domain") or default_domain)
            domain = requested_domain if requested_domain in PROFILE_DOMAINS else default_domain
            memory_review_status = str(memory.get("review_status") or "confirmed")
            source_type = str(memory.get("source_type") or "manual")
            review_status = "confirmed" if source_type == "manual" else "pending"
            active = (
                memory.get("status") == "active"
                and bool(memory.get("use_in_context", True))
                and memory_review_status in {"confirmed", "corrected"}
            )
            self._archive_memory_claims(owner_id, memory_id)
            if not active:
                continue
            self._repository.upsert_claim(
                owner_id,
                {
                    "domain": domain,
                    "profile_key": str(metadata.get("profile_key") or f"memory:{memory_id}"),
                    "value": memory.get("content"),
                    "summary": memory.get("title"),
                    "rationale": "Added to your profile understanding with explicit permission.",
                    "confidence": memory.get("confidence", 1.0),
                    "review_status": review_status,
                    "evidence_refs": [{"type": "memory", "id": memory_id}],
                    "first_observed_at": memory.get("created_at"),
                    "last_observed_at": memory.get("updated_at"),
                    "status": "active" if active else "archived",
                },
            )

    def _archive_memory_claims(self, owner_id: str, memory_id: str) -> None:
        for claim in self._repository.list_claims(owner_id, status="active", limit=500):
            evidence_refs = claim.get("evidence_refs") or []
            if any(
                isinstance(item, Mapping)
                and item.get("type") == "memory"
                and str(item.get("id") or "") == memory_id
                for item in evidence_refs
            ):
                self._repository.update_claim(
                    owner_id, claim["claim_id"], {"status": "archived"}
                )

    def view(self, owner_id: str) -> Dict[str, Any]:
        claims = list(self._repository.list_claims(owner_id, status="active", limit=500))
        overrides = {
            (item["domain"], item["profile_key"]): item
            for item in self._repository.list_overrides(owner_id, status="active")
        }
        raw = []
        effective = []
        for claim in claims:
            item = dict(claim)
            override = overrides.get((claim["domain"], claim["profile_key"]))
            item["override"] = override
            raw.append(item)
            if claim.get("review_status") == "rejected":
                continue
            if override and override.get("operation") == "suppress":
                continue
            effective_item = dict(item)
            if override and override.get("operation") == "replace":
                effective_item["value"] = override.get("value")
                effective_item["effective_source"] = "user_override"
            else:
                effective_item["effective_source"] = "claim"
            effective_item["context_eligible"] = (
                effective_item.get("review_status") in {"confirmed", "corrected"}
            )
            effective.append(effective_item)

        groups = {
            domain: [item for item in effective if item.get("domain") == domain]
            for domain in PROFILE_DOMAINS
        }
        return {
            "raw_claims": raw,
            "effective_claims": effective,
            "groups": groups,
            "stats": {
                "total": len(raw),
                "pending": sum(item.get("review_status") == "pending" for item in raw),
                "confirmed": sum(item.get("review_status") == "confirmed" for item in raw),
                "corrected": sum(item.get("review_status") == "corrected" for item in raw),
                "rejected": sum(item.get("review_status") == "rejected" for item in raw),
            },
        }

    def review_claim(
        self,
        owner_id: str,
        claim_id: str,
        *,
        decision: str,
        value: Any = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        if decision not in CLAIM_REVIEW_STATUSES:
            raise PersonalContextError("Invalid profile review decision.", "INVALID_PROFILE_REVIEW")
        claim = self._repository.get_claim(owner_id, claim_id)
        if claim is None:
            raise PersonalContextError("Profile claim not found.", "PROFILE_CLAIM_NOT_FOUND", 404)
        if decision == "corrected" and (value is None or str(value).strip() == ""):
            raise PersonalContextError("A corrected value is required.", "PROFILE_CORRECTION_REQUIRED")
        if not self._repository.update_claim(owner_id, claim_id, {"review_status": decision}):
            raise PersonalContextError("Profile claim changed before review.", "PROFILE_STATE_CONFLICT", 409)
        if decision == "corrected":
            self._repository.upsert_override(
                owner_id,
                {
                    "domain": claim["domain"],
                    "profile_key": claim["profile_key"],
                    "operation": "replace",
                    "value": value,
                    "reason": str(reason or "").strip()[:500],
                    "status": "active",
                },
            )
        elif decision == "rejected":
            self._repository.upsert_override(
                owner_id,
                {
                    "domain": claim["domain"],
                    "profile_key": claim["profile_key"],
                    "operation": "suppress",
                    "value": None,
                    "reason": str(reason or "").strip()[:500],
                    "status": "active",
                },
            )
        else:
            self._repository.archive_override(owner_id, claim["domain"], claim["profile_key"])
        updated = self._repository.get_claim(owner_id, claim_id)
        if updated is None:
            raise PersonalContextError("Profile claim not found.", "PROFILE_CLAIM_NOT_FOUND", 404)
        self.upsert_observation(
            owner_id,
            {
                "kind": "feedback",
                "summary": f"User reviewed a profile understanding ({decision}).",
                "source_type": "profile_claim_review",
                "source_ref": f"claim:{claim_id}:review",
                "attributes": {
                    "claim_id": claim_id,
                    "domain": updated.get("domain"),
                    "decision": decision,
                    "has_correction": decision == "corrected",
                    "has_reason": bool(str(reason or "").strip()),
                },
                "weight": 1.0,
                "observed_at": updated.get("updated_at"),
                "sensitivity": "private",
                "status": "active",
            },
        )
        return updated

    def _normalize_claim(self, values: Mapping[str, Any]) -> Dict[str, Any]:
        domain = str(values.get("domain") or "")
        if domain not in PROFILE_DOMAINS:
            raise PersonalContextError("Invalid profile domain.", "INVALID_PROFILE_DOMAIN")
        review_status = str(values.get("review_status") or "pending")
        if review_status not in CLAIM_REVIEW_STATUSES:
            raise PersonalContextError("Invalid profile review status.", "INVALID_PROFILE_REVIEW")
        status = str(values.get("status") or "active")
        if status not in PROFILE_RECORD_STATUSES:
            raise PersonalContextError("Invalid profile claim status.", "INVALID_PROFILE_CLAIM_STATUS")
        evidence = values.get("evidence_refs") or []
        if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
            raise PersonalContextError("Invalid profile evidence references.", "INVALID_PROFILE_EVIDENCE")
        return {
            "domain": domain,
            "profile_key": _profile_key(values.get("profile_key")),
            "value": values.get("value"),
            "summary": _clean_text(values.get("summary"), maximum=240, field="profile_summary"),
            "rationale": str(values.get("rationale") or "").strip()[:1000],
            "confidence": _confidence(values.get("confidence", 0.5)),
            "review_status": review_status,
            "evidence_refs": list(evidence),
            "first_observed_at": str(values.get("first_observed_at") or "").strip() or None,
            "last_observed_at": str(values.get("last_observed_at") or "").strip() or None,
            "status": status,
        }
