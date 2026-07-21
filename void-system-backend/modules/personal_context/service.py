"""Personal Context use cases for settings, memories, snapshots, and briefings."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from core.personal_context_contracts import PersonalContextError, PersonalContextRepository
from modules.personal_context.context import ContextAssembler, SECTION_ORDER
from modules.personal_context.evidence import ProfileEvidenceCollector
from modules.personal_context.inference import MINIMUM_PROFILE_EVIDENCE, ProfileInference
from modules.personal_context.layered_profile import LayeredProfileWorkspace
from modules.personal_context.policy import resolve_context_policy
from modules.personal_context.profile import ProfileCognition


DEFAULT_PERMISSIONS = {
    "profile": False,
    "goals": True,
    "runs": True,
    "growth": True,
    "memories": True,
    "knowledge": False,
    "rewards": False,
}
MEMORY_TYPES = {"fact", "preference", "episode", "inference"}
MEMORY_STATUSES = {"active", "archived"}
MEMORY_REVIEW_STATUSES = {"pending", "confirmed", "corrected", "rejected"}
CONTEXT_ELIGIBLE_MEMORY_REVIEWS = {"confirmed", "corrected"}
TONES = {"calm", "warm", "direct"}
INITIATIVES = {"quiet", "balanced", "proactive"}
DEFAULT_PERSONA = {
    "name": "系统精灵",
    "role": "协作伙伴",
    "brief": "",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PersonalContext:
    """Deep module that owns user consent, memory semantics, and context rendering."""

    def __init__(
        self,
        repository: PersonalContextRepository,
        assembler: ContextAssembler,
        profile_cognition: Optional[ProfileCognition] = None,
        profile_inference: Optional[ProfileInference] = None,
        profile_evidence_collector: Optional[ProfileEvidenceCollector] = None,
        layered_profile: Optional[LayeredProfileWorkspace] = None,
    ) -> None:
        self._repository = repository
        self._assembler = assembler
        self._profile = profile_cognition or ProfileCognition(repository)
        self._profile_inference = profile_inference
        self._profile_evidence_collector = profile_evidence_collector
        self._layered_profile = layered_profile or LayeredProfileWorkspace()

    def get_settings(self, owner_id: str) -> Dict[str, Any]:
        stored = self._repository.get_settings(owner_id)
        if stored is None:
            return {
                "owner_id": owner_id,
                "enabled": True,
                "tone": "calm",
                "initiative": "balanced",
                "persona": dict(DEFAULT_PERSONA),
                "permissions": dict(DEFAULT_PERMISSIONS),
                "created_at": None,
                "updated_at": None,
            }
        stored["permissions"] = self._permissions(stored.get("permissions"))
        stored["persona"] = self._persona(stored.get("persona"), strict=False)
        return stored

    def update_settings(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        current = self.get_settings(owner_id)
        tone = str(values.get("tone", current["tone"]))
        initiative = str(values.get("initiative", current["initiative"]))
        if tone not in TONES:
            raise PersonalContextError("Invalid companion tone.", "INVALID_COMPANION_TONE")
        if initiative not in INITIATIVES:
            raise PersonalContextError(
                "Invalid companion initiative.", "INVALID_COMPANION_INITIATIVE"
            )
        persona = self._persona(
            values.get("persona", current["persona"]),
            fallback=current["persona"],
        )
        permissions = dict(current["permissions"])
        submitted = values.get("permissions")
        if submitted is not None:
            if not isinstance(submitted, Mapping):
                raise PersonalContextError(
                    "Permissions must be an object.", "INVALID_CONTEXT_PERMISSIONS"
                )
            unknown = set(submitted) - set(DEFAULT_PERMISSIONS)
            if unknown:
                raise PersonalContextError(
                    "Unknown context permission.", "INVALID_CONTEXT_PERMISSION"
                )
            permissions.update({key: bool(value) for key, value in submitted.items()})
        return self._repository.upsert_settings(
            owner_id,
            {
                "enabled": bool(values.get("enabled", current["enabled"])),
                "tone": tone,
                "initiative": initiative,
                "persona": persona,
                "permissions": permissions,
            },
        )

    @staticmethod
    def _persona(
        value: Any,
        *,
        fallback: Optional[Mapping[str, Any]] = None,
        strict: bool = True,
    ) -> Dict[str, str]:
        """Return a bounded, presentation-only companion identity.

        Inputs: a partial API payload or a persisted JSON value. Output: the
        normalized name, role, and brief used only by persona-chain language
        instructions. Invalid persisted historical values fall back safely;
        invalid client input raises a stable domain error.
        """
        base = dict(DEFAULT_PERSONA)
        if isinstance(fallback, Mapping):
            for key in base:
                candidate = fallback.get(key)
                if isinstance(candidate, str):
                    base[key] = candidate.strip()
        if value is None:
            return base
        if not isinstance(value, Mapping):
            if strict:
                raise PersonalContextError("Persona must be an object.", "INVALID_COMPANION_PERSONA")
            return dict(DEFAULT_PERSONA)
        unknown = set(value) - set(DEFAULT_PERSONA)
        if unknown:
            raise PersonalContextError("Unknown persona field.", "INVALID_COMPANION_PERSONA")
        limits = {"name": (1, 48), "role": (1, 80), "brief": (0, 500)}
        for key, raw_value in value.items():
            if not isinstance(raw_value, str):
                raise PersonalContextError("Persona fields must be text.", "INVALID_COMPANION_PERSONA")
            cleaned = raw_value.strip()
            minimum, maximum = limits[key]
            if not minimum <= len(cleaned) <= maximum:
                raise PersonalContextError("Persona field length is invalid.", "INVALID_COMPANION_PERSONA")
            base[key] = cleaned
        return base

    def create_memory(
        self, owner_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        normalized = self._normalize_memory(
            self._with_profile_consent(values), partial=False
        )
        memory = self._repository.create_memory(owner_id, normalized)
        self._profile.sync_memories(owner_id, [memory])
        return memory

    def list_memories(
        self,
        owner_id: str,
        *,
        memory_type: Optional[str] = None,
        status: Optional[str] = None,
        review_status: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[Dict[str, Any]]:
        if memory_type is not None and memory_type not in MEMORY_TYPES:
            raise PersonalContextError("Invalid memory type.", "INVALID_MEMORY_TYPE")
        if status is not None and status not in MEMORY_STATUSES:
            raise PersonalContextError("Invalid memory status.", "INVALID_MEMORY_STATUS")
        if review_status is not None and review_status not in MEMORY_REVIEW_STATUSES:
            raise PersonalContextError(
                "Invalid memory review status.", "INVALID_MEMORY_REVIEW_STATUS"
            )
        return self._repository.list_memories(
            owner_id,
            memory_type=memory_type,
            status=status,
            review_status=review_status,
            limit=limit,
        )

    def list_memory_suggestions(
        self, owner_id: str, *, limit: int = 100
    ) -> Sequence[Dict[str, Any]]:
        return self._repository.list_memories(
            owner_id, status="active", review_status="pending", limit=limit
        )

    def get_profile_view(self, owner_id: str) -> Dict[str, Any]:
        """Return the canonical layered profile workspace for one owner.

        Inputs:
            owner_id: The account whose consented signals and profile records are read.
        Outputs:
            A public workspace with signals, deterministic patterns, pending
            hypotheses, confirmed facets, and an explicit context projection.
        Privacy:
            Raw task titles, chat content, document bodies, and storage IDs are
            never included in the returned payload.
        """
        settings = self.get_settings(owner_id)
        memories = self._repository.list_memories(owner_id, limit=500)
        self._profile.sync_memories(owner_id, memories)
        if settings["permissions"]["profile"] and self._profile_evidence_collector is not None:
            self._profile_evidence_collector.collect(owner_id)
        profile_view = self._profile.view(owner_id)
        workspace = self._layered_profile.build(settings=settings, profile_view=profile_view)
        workspace["evidence"] = self._profile_evidence_state(
            settings, profile_view["signals"], memories
        )
        return workspace

    @staticmethod
    def _profile_evidence_state(
        settings: Mapping[str, Any],
        signals: Sequence[Mapping[str, Any]],
        memories: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        """Describe inference readiness without leaking private source content."""
        eligible = [
            item for item in signals
            if item.get("status") == "active"
            and item.get("sensitivity") in {"personal", "private"}
            and str(item.get("summary") or "").strip()
        ]
        source_type_counts: Dict[str, int] = {}
        for item in eligible:
            source_type = str(item.get("source_type") or "manual")
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
        explicit_memory_count = sum(
            1 for memory in memories
            if memory.get("status") == "active"
            and bool(memory.get("use_in_context", True))
            and str(memory.get("review_status") or "confirmed") in CONTEXT_ELIGIBLE_MEMORY_REVIEWS
            and isinstance(memory.get("metadata"), Mapping)
            and memory["metadata"].get("contribute_to_profile") is True
        )
        profile_permission = bool((settings.get("permissions") or {}).get("profile"))
        return {
            "eligible_signal_count": len(eligible),
            "minimum_signal_count": MINIMUM_PROFILE_EVIDENCE,
            "permission_enabled": profile_permission,
            "ready_for_inference": profile_permission and len(eligible) >= MINIMUM_PROFILE_EVIDENCE,
            "sources": [
                {"key": "task_history", "count": source_type_counts.get("workspace_history_summary", 0), "inference_eligible": True},
                {"key": "task_reviews", "count": source_type_counts.get("task_run_review", 0), "inference_eligible": True},
                {"key": "profile_feedback", "count": source_type_counts.get("profile_hypothesis_review", 0), "inference_eligible": True},
                {"key": "manual_evidence", "count": sum(count for source_type, count in source_type_counts.items() if source_type not in {"workspace_history_summary", "task_run_review", "profile_hypothesis_review", "explicit_memory"}), "inference_eligible": True},
                {"key": "explicit_memories", "count": explicit_memory_count, "inference_eligible": False},
            ],
        }

    def infer_profile_hypotheses(
        self,
        owner_id: str,
        *,
        max_signals: int = 24,
        max_hypotheses: int = 4,
    ) -> Dict[str, Any]:
        """Ask the configured model to organize safe signals into reviewable hypotheses."""
        settings = self.get_settings(owner_id)
        if not settings["permissions"]["profile"]:
            raise PersonalContextError(
                "Enable profile understanding before asking AI to organize hypotheses.",
                "PROFILE_PERMISSION_REQUIRED", 403,
            )
        if self._profile_inference is None:
            raise PersonalContextError("Profile inference is unavailable.", "PROFILE_INFERENCE_UNAVAILABLE", 503)
        if not 3 <= max_signals <= 48 or not 1 <= max_hypotheses <= 6:
            raise PersonalContextError("Invalid profile inference limits.", "INVALID_PROFILE_INFERENCE_LIMITS")
        collected = (
            self._profile_evidence_collector.collect(owner_id)
            if self._profile_evidence_collector is not None
            else []
        )
        signals = self._profile.list_signals(owner_id, status="active", limit=max_signals)
        candidates = self._profile_inference.infer(signals, max_hypotheses=max_hypotheses)
        hypotheses = []
        for candidate in candidates:
            try:
                hypotheses.append(self._profile.create_hypothesis(owner_id, candidate))
            except PersonalContextError as exc:
                if exc.code in {"PROFILE_HYPOTHESIS_SUPPRESSED", "PROFILE_FACET_ALREADY_CONFIRMED"}:
                    continue
                raise
        return {
            "hypotheses": hypotheses,
            "signal_count": len([
                item for item in signals if item.get("sensitivity") in {"personal", "private"}
            ]),
            "review_required": True,
            "refreshed_signal_count": len(collected),
        }

    def review_profile_hypothesis(
        self, owner_id: str, hypothesis_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        return self._profile.review_hypothesis(
            owner_id,
            hypothesis_id,
            decision=str(values.get("decision") or ""),
            value=values.get("value"),
            reason=str(values.get("reason") or ""),
        )

    def update_memory(
        self, owner_id: str, memory_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        current = self._require_memory(owner_id, memory_id)
        updates = self._normalize_memory(
            self._with_profile_consent(values, existing_metadata=current.get("metadata")),
            partial=True,
        )
        if not updates:
            return self._require_memory(owner_id, memory_id)
        if not self._repository.update_memory(owner_id, memory_id, updates):
            raise PersonalContextError(
                "Memory changed before it could be updated.", "MEMORY_STATE_CONFLICT", 409
            )
        memory = self._require_memory(owner_id, memory_id)
        self._profile.sync_memories(owner_id, [memory])
        return memory

    def review_memory(
        self, owner_id: str, memory_id: str, values: Mapping[str, Any]
    ) -> Dict[str, Any]:
        self._require_memory(owner_id, memory_id)
        decision = str(values.get("decision") or "").strip()
        if decision not in {"confirmed", "corrected", "rejected"}:
            raise PersonalContextError("Invalid memory review decision.", "INVALID_MEMORY_REVIEW")

        updates: Dict[str, Any] = {
            "review_status": decision,
            "review_note": str(values.get("reason") or "").strip()[:500],
            "reviewed_at": _now(),
        }
        if decision == "corrected":
            if not str(values.get("content") or "").strip():
                raise PersonalContextError(
                    "A corrected memory needs content.", "MEMORY_CORRECTION_REQUIRED"
                )
            corrections = {
                key: values[key]
                for key in ("memory_type", "title", "content", "use_in_context")
                if key in values and values[key] is not None
            }
            updates.update(self._normalize_memory(corrections, partial=True))
            updates["status"] = "active"
            updates.setdefault("use_in_context", True)
        elif decision == "confirmed":
            updates["status"] = "active"
            updates["use_in_context"] = bool(values.get("use_in_context", True))
        else:
            updates.update({"status": "archived", "use_in_context": False})

        if not self._repository.update_memory(owner_id, memory_id, updates):
            raise PersonalContextError("Memory changed before review.", "MEMORY_STATE_CONFLICT", 409)
        reviewed = self._require_memory(owner_id, memory_id)
        self._profile.sync_memories(owner_id, [reviewed])
        return reviewed

    def delete_memory(self, owner_id: str, memory_id: str) -> None:
        self._require_memory(owner_id, memory_id)
        if not self._repository.update_memory(
            owner_id, memory_id, {"status": "archived", "use_in_context": False}
        ):
            raise PersonalContextError("Memory not found.", "MEMORY_NOT_FOUND", 404)
        self._profile.sync_memories(owner_id, [self._require_memory(owner_id, memory_id)])

    def purge_memory(self, owner_id: str, memory_id: str) -> None:
        memory = self._require_memory(owner_id, memory_id)
        if memory.get("status") != "archived":
            raise PersonalContextError(
                "Archive a memory before permanently removing it.",
                "MEMORY_PURGE_REQUIRES_ARCHIVE",
                409,
            )
        if not self._repository.delete_memory(owner_id, memory_id):
            raise PersonalContextError("Memory not found.", "MEMORY_NOT_FOUND", 404)

    def build_context(
        self,
        owner_id: str,
        profile: Mapping[str, Any],
        *,
        purpose: str = "companion_context",
        requested_sections: Optional[Sequence[str]] = None,
        item_budget: int = 24,
        profile_domains: Optional[Sequence[str]] = None,
        include_account_profile: bool = True,
    ) -> Dict[str, Any]:
        settings = self.get_settings(owner_id)
        requested = self._requested_sections(requested_sections)
        if not 1 <= item_budget <= 100:
            raise PersonalContextError("Invalid context budget.", "INVALID_CONTEXT_BUDGET")
        if not str(purpose).strip() or len(str(purpose)) > 80:
            raise PersonalContextError("Invalid context purpose.", "INVALID_CONTEXT_PURPOSE")

        if settings["enabled"]:
            memories = self._repository.list_memories(owner_id, limit=500)
            self._profile.sync_memories(owner_id, memories)
            profile_view = self._profile.view(owner_id)
            snapshot = self._assembler.collect(
                owner_id,
                profile,
                memories,
                profile_view=profile_view,
                permissions=settings["permissions"],
                requested_sections=requested,
                item_budget=item_budget,
                profile_domains=profile_domains,
                include_account_profile=include_account_profile,
            )
        else:
            snapshot = {
                "generated_at": _now(),
                "requested_sections": requested,
                "included_sections": [],
                "omitted_sections": [
                    {"section": section, "reason": "companion_disabled"}
                    for section in requested
                ],
                "item_budget": item_budget,
                "item_count": 0,
                "sections": {},
                "sources": [
                    {
                        "section": section,
                        "included": 0,
                        "available": 0,
                        "truncated": False,
                        "permission": bool(settings["permissions"].get(section, False)),
                        "decision": "excluded",
                        "reason": "Companion is paused.",
                    }
                    for section in requested
                ],
                "selected_references": [],
            }
        snapshot["purpose"] = str(purpose)
        snapshot["companion_enabled"] = settings["enabled"]
        snapshot["permissions"] = settings["permissions"]
        audit = self._repository.record_access(
            owner_id,
            {
                "purpose": str(purpose),
                "requested_sections": requested,
                "included_sections": snapshot["included_sections"],
                "item_count": snapshot["item_count"],
                "source_decisions": snapshot["sources"],
                "selected_references": snapshot["selected_references"],
                "omitted_sections": snapshot["omitted_sections"],
            },
        )
        snapshot["audit_id"] = audit.get("audit_id")
        return snapshot

    def build_ai_context(
        self,
        owner_id: str,
        profile: Mapping[str, Any],
        *,
        purpose: str,
    ) -> Dict[str, Any]:
        policy = resolve_context_policy(purpose)
        snapshot = self.build_context(
            owner_id,
            profile,
            purpose=policy.purpose,
            requested_sections=policy.requested_sections,
            item_budget=policy.item_budget,
            profile_domains=policy.profile_domains,
            include_account_profile=policy.include_account_profile,
        )
        snapshot["manifest"] = {
            "purpose": policy.purpose,
            "used": bool(snapshot["item_count"]),
            "audit_id": snapshot["audit_id"],
            "included_sections": snapshot["included_sections"],
            "omitted_sections": snapshot["omitted_sections"],
            "item_count": snapshot["item_count"],
            "user_explanation": policy.user_explanation,
            "review_rule": "Only confirmed or corrected profile understandings are eligible.",
        }
        return snapshot

    @staticmethod
    def render_ai_context(snapshot: Mapping[str, Any]) -> str:
        rows = []
        for section in snapshot.get("included_sections", []):
            for item in snapshot.get("sections", {}).get(section, []):
                title = " ".join(str(item.get("title") or "").split())
                summary = " ".join(str(item.get("summary") or "").split())
                if title and summary:
                    rows.append(f"[{section}] {title}: {summary}")
        return "\n".join(rows)

    def build_briefing(
        self,
        owner_id: str,
        profile: Mapping[str, Any],
        *,
        item_budget: int = 24,
    ) -> Dict[str, Any]:
        settings = self.get_settings(owner_id)
        policy = resolve_context_policy("companion_briefing")
        snapshot = self.build_context(
            owner_id,
            profile,
            purpose=policy.purpose,
            requested_sections=policy.requested_sections,
            item_budget=min(item_budget, policy.item_budget),
            profile_domains=policy.profile_domains,
            include_account_profile=policy.include_account_profile,
        )
        goals = snapshot["sections"].get("goals", [])
        runs = snapshot["sections"].get("runs", [])
        focus = [*runs[:2], *goals[: max(0, 3 - len(runs[:2]))]]
        suggestions = self._suggestions(goals, runs)
        name = str(profile.get("username") or "there")
        if not settings["enabled"]:
            headline = "Companion is paused"
            message = "Your personal context is not being used. You can enable it in companion settings."
        elif runs:
            headline = "Continue what is already moving"
            message = f"{name}, you have {len(runs)} active execution attempt(s). The next useful move is ready."
        elif goals:
            headline = "Turn an active goal into a concrete run"
            message = f"{name}, your direction is clear. Choose one goal and define its next reviewable steps."
        else:
            headline = "Choose one outcome worth moving"
            message = f"{name}, start with a small goal that can produce visible evidence this week."
        return {
            "generated_at": snapshot["generated_at"],
            "headline": headline,
            "message": message,
            "tone": settings["tone"],
            "initiative": settings["initiative"],
            "focus_items": focus,
            "suggestions": suggestions,
            "context": {
                "audit_id": snapshot["audit_id"],
                "included_sections": snapshot["included_sections"],
                "item_count": snapshot["item_count"],
                "sources": snapshot["sources"],
                "omitted_sections": snapshot["omitted_sections"],
            },
        }

    def access_log(self, owner_id: str, limit: int = 50) -> Sequence[Dict[str, Any]]:
        return self._repository.list_access_log(owner_id, limit)

    def _require_memory(self, owner_id: str, memory_id: str) -> Dict[str, Any]:
        memory = self._repository.get_memory(owner_id, memory_id)
        if memory is None:
            raise PersonalContextError("Memory not found.", "MEMORY_NOT_FOUND", 404)
        return memory

    def _normalize_memory(
        self, values: Mapping[str, Any], *, partial: bool
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        defaults = {
            "memory_type": "fact",
            "title": "",
            "content": "",
            "source_type": "manual",
            "source_ref": None,
            "confidence": 1.0,
            "use_in_context": True,
            "status": "active",
            "review_status": "confirmed",
            "evidence_refs": [],
            "review_note": "",
            "reviewed_at": _now(),
            "expires_at": None,
            "metadata": {},
        }
        for field, default in defaults.items():
            if field in values or not partial:
                result[field] = values.get(field, default)
        if "memory_type" in result and result["memory_type"] not in MEMORY_TYPES:
            raise PersonalContextError("Invalid memory type.", "INVALID_MEMORY_TYPE")
        if "status" in result and result["status"] not in MEMORY_STATUSES:
            raise PersonalContextError("Invalid memory status.", "INVALID_MEMORY_STATUS")
        if (
            "review_status" in result
            and result["review_status"] not in MEMORY_REVIEW_STATUSES
        ):
            raise PersonalContextError(
                "Invalid memory review status.", "INVALID_MEMORY_REVIEW_STATUS"
            )
        for field, maximum in (("title", 160), ("content", 4000), ("source_type", 60)):
            if field in result:
                result[field] = str(result[field] or "").strip()
                if not result[field] or len(result[field]) > maximum:
                    raise PersonalContextError(
                        f"Invalid memory {field}.", f"INVALID_MEMORY_{field.upper()}"
                    )
        if "source_ref" in result and result["source_ref"] is not None:
            result["source_ref"] = str(result["source_ref"]).strip()[:500] or None
        if "confidence" in result:
            try:
                result["confidence"] = float(result["confidence"])
            except (TypeError, ValueError) as exc:
                raise PersonalContextError(
                    "Invalid memory confidence.", "INVALID_MEMORY_CONFIDENCE"
                ) from exc
            if not 0 <= result["confidence"] <= 1:
                raise PersonalContextError(
                    "Invalid memory confidence.", "INVALID_MEMORY_CONFIDENCE"
                )
        if "use_in_context" in result:
            result["use_in_context"] = bool(result["use_in_context"])
        if "evidence_refs" in result:
            evidence_refs = result["evidence_refs"]
            if (
                isinstance(evidence_refs, (str, bytes))
                or not isinstance(evidence_refs, Sequence)
                or len(evidence_refs) > 20
                or any(not isinstance(item, Mapping) for item in evidence_refs)
            ):
                raise PersonalContextError(
                    "Invalid memory evidence.", "INVALID_MEMORY_EVIDENCE"
                )
            result["evidence_refs"] = [dict(item) for item in evidence_refs]
        if "review_note" in result:
            result["review_note"] = str(result["review_note"] or "").strip()
            if len(result["review_note"]) > 500:
                raise PersonalContextError(
                    "Invalid memory review note.", "INVALID_MEMORY_REVIEW_NOTE"
                )
        for field in ("reviewed_at", "expires_at"):
            if field in result and result[field] is not None:
                result[field] = str(result[field]).strip()
                if len(result[field]) > 80:
                    raise PersonalContextError(
                        f"Invalid memory {field}.", f"INVALID_MEMORY_{field.upper()}"
                    )
        if "metadata" in result:
            if not isinstance(result["metadata"], Mapping):
                raise PersonalContextError(
                    "Invalid memory metadata.", "INVALID_MEMORY_METADATA"
                )
            result["metadata"] = dict(result["metadata"])
        return result

    @staticmethod
    def _with_profile_consent(
        values: Mapping[str, Any], *, existing_metadata: Any = None
    ) -> Dict[str, Any]:
        normalized = dict(values)
        if "contribute_to_profile" not in normalized:
            return normalized
        metadata = dict(existing_metadata) if isinstance(existing_metadata, Mapping) else {}
        submitted_metadata = normalized.get("metadata")
        if isinstance(submitted_metadata, Mapping):
            metadata.update(submitted_metadata)
        metadata["contribute_to_profile"] = bool(normalized.pop("contribute_to_profile"))
        normalized["metadata"] = metadata
        return normalized

    @staticmethod
    def _permissions(values: Any) -> Dict[str, bool]:
        permissions = dict(DEFAULT_PERMISSIONS)
        if isinstance(values, Mapping):
            permissions.update(
                {key: bool(value) for key, value in values.items() if key in permissions}
            )
        return permissions

    @staticmethod
    def _requested_sections(values: Optional[Sequence[str]]) -> list[str]:
        if values is None:
            return list(SECTION_ORDER)
        requested = list(dict.fromkeys(str(value) for value in values))
        if not requested or set(requested) - set(SECTION_ORDER):
            raise PersonalContextError(
                "Invalid context section.", "INVALID_CONTEXT_SECTION"
            )
        return [section for section in SECTION_ORDER if section in requested]

    @staticmethod
    def _suggestions(
        goals: Sequence[Mapping[str, Any]], runs: Sequence[Mapping[str, Any]]
    ) -> list[Dict[str, Any]]:
        suggestions: list[Dict[str, Any]] = []
        running = next((item for item in runs if item["data"].get("status") == "running"), None)
        queued = next((item for item in runs if item["data"].get("status") == "queued"), None)
        if running:
            suggestions.append({
                "kind": "continue_run", "title": f"Continue {running['title']}",
                "reason": "It is already in progress.", "reference": running["reference"],
            })
        if queued:
            suggestions.append({
                "kind": "start_run", "title": f"Start {queued['title']}",
                "reason": "Its plan is ready to begin.", "reference": queued["reference"],
            })
        goal_without_run = next(
            (item for item in goals if int(item["data"].get("run_count") or 0) == 0), None
        )
        if goal_without_run:
            suggestions.append({
                "kind": "plan_goal", "title": f"Plan {goal_without_run['title']}",
                "reason": "This goal has no execution attempt yet.",
                "reference": goal_without_run["reference"],
            })
        if not suggestions:
            suggestions.append({
                "kind": "create_goal", "title": "Create a focused goal",
                "reason": "A clear outcome gives the workspace something concrete to support.",
                "reference": None,
            })
        return suggestions[:3]
