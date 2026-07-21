"""Budgeted context assembly with provenance and permission enforcement."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from core.personal_context_contracts import (
    GrowthContextSource,
    KnowledgeContextSource,
    TaskContextSource,
)


SECTION_ORDER = ("profile", "goals", "runs", "growth", "memories", "knowledge", "rewards")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_expired(value: Any) -> bool:
    if value in (None, ""):
        return False
    try:
        expires_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


def _memory_priority(memory: Mapping[str, Any]) -> tuple[int, float, float]:
    kind_order = {"fact": 0, "preference": 1, "episode": 2, "inference": 3}
    try:
        confidence = float(memory.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0
    try:
        updated_at = datetime.fromisoformat(
            str(memory.get("updated_at") or "").replace("Z", "+00:00")
        )
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        updated_timestamp = updated_at.timestamp()
    except (TypeError, ValueError):
        updated_timestamp = 0
    return (
        kind_order.get(str(memory.get("memory_type") or "inference"), 4),
        -confidence,
        -updated_timestamp,
    )


def _text(value: Any, limit: int = 240) -> str:
    normalized = " ".join(str(value or "").split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1].rstrip() + "..."


def _item(
    section: str,
    kind: str,
    item_id: str,
    title: str,
    summary: str,
    *,
    updated_at: Optional[str] = None,
    sensitivity: str = "personal",
    data: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "id": f"{section}:{item_id}",
        "section": section,
        "kind": kind,
        "title": _text(title, 160),
        "summary": _text(summary),
        "reference": {"type": kind, "id": item_id},
        "provenance": {"source": section, "source_ref": item_id},
        "freshness": {"updated_at": updated_at},
        "sensitivity": sensitivity,
        "data": dict(data or {}),
    }


class ContextAssembler:
    """Collect portable context from public module interfaces under a hard item budget."""

    def __init__(
        self,
        tasks: TaskContextSource,
        growth: GrowthContextSource,
        knowledge: KnowledgeContextSource,
    ) -> None:
        self._tasks = tasks
        self._growth = growth
        self._knowledge = knowledge

    def collect(
        self,
        owner_id: str,
        profile: Mapping[str, Any],
        memories: Sequence[Mapping[str, Any]],
        *,
        profile_view: Optional[Mapping[str, Any]] = None,
        permissions: Mapping[str, bool],
        requested_sections: Sequence[str],
        item_budget: int,
        profile_domains: Optional[Sequence[str]] = None,
        include_account_profile: bool = True,
    ) -> Dict[str, Any]:
        requested = [section for section in SECTION_ORDER if section in requested_sections]
        allowed = [section for section in requested if permissions.get(section, False)]
        candidates: Dict[str, list[Dict[str, Any]]] = {}
        for section in allowed:
            candidates[section] = self._collect_section(
                section, owner_id, profile, profile_view or {}, memories, item_budget,
                profile_domains=profile_domains, include_account_profile=include_account_profile,
            )

        selected: Dict[str, list[Dict[str, Any]]] = {section: [] for section in allowed}
        remaining = item_budget
        cursor = 0
        while remaining > 0:
            added = False
            for section in allowed:
                items = candidates[section]
                if cursor < len(items):
                    item = dict(items[cursor])
                    selection_reason = item.pop(
                        "_selection_reason",
                        "Included by your permission and the context budget.",
                    )
                    item["selection"] = {
                        "reason": selection_reason,
                        "candidate_rank": cursor + 1,
                    }
                    selected[section].append(item)
                    remaining -= 1
                    added = True
                    if remaining == 0:
                        break
            if not added:
                break
            cursor += 1

        included = [section for section in allowed if selected[section]]
        sources: list[Dict[str, Any]] = []
        omitted_sections: list[Dict[str, str]] = []
        for section in requested:
            if not permissions.get(section, False):
                sources.append({
                    "section": section,
                    "included": 0,
                    "available": 0,
                    "truncated": False,
                    "permission": False,
                    "decision": "excluded",
                    "reason": "Not enabled in companion settings.",
                })
                omitted_sections.append({"section": section, "reason": "permission"})
                continue
            available = len(candidates[section])
            count = len(selected[section])
            if count == 0 and available:
                reason = "Context budget was used by earlier selected items."
                decision = "omitted"
                omitted_sections.append({"section": section, "reason": "budget"})
            elif count == 0:
                reason = "No current items were available."
                decision = "empty"
            elif count < available:
                reason = "Only the highest-priority available items fit the context budget."
                decision = "included"
                omitted_sections.append({"section": section, "reason": "budget"})
            else:
                reason = "All current items fit the context budget."
                decision = "included"
            sources.append({
                "section": section,
                "included": count,
                "available": available,
                "truncated": count < available,
                "permission": True,
                "decision": decision,
                "reason": reason,
            })

        selected_references = [
            {"section": section, **dict(item["reference"])}
            for section, items in selected.items()
            for item in items
        ]
        return {
            "generated_at": _now(),
            "requested_sections": list(requested_sections),
            "included_sections": included,
            "omitted_sections": omitted_sections,
            "item_budget": item_budget,
            "item_count": sum(len(items) for items in selected.values()),
            "sections": selected,
            "sources": sources,
            "selected_references": selected_references,
        }

    def _collect_section(
        self,
        section: str,
        owner_id: str,
        profile: Mapping[str, Any],
        profile_view: Mapping[str, Any],
        memories: Sequence[Mapping[str, Any]],
        limit: int,
        *,
        profile_domains: Optional[Sequence[str]] = None,
        include_account_profile: bool = True,
    ) -> list[Dict[str, Any]]:
        if section == "profile":
            items = []
            if include_account_profile:
                items.append(
                    _item(
                        "profile",
                        "user_profile",
                        owner_id,
                        str(profile.get("username") or "User"),
                        "Personal account profile available to the companion.",
                        updated_at=profile.get("updated_at"),
                        data={"username": profile.get("username"), "role": profile.get("role", "user")},
                    )
                )
            allowed_domains = set(profile_domains) if profile_domains is not None else None
            for facet in profile_view.get("facets", []):
                if facet.get("status") != "active" or not facet.get("context_enabled", False):
                    continue
                if allowed_domains is not None and facet.get("domain") not in allowed_domains:
                    continue
                facet_id = str(facet.get("facet_id") or facet.get("profile_key"))
                facet_item = _item(
                    "profile",
                    "profile_facet",
                    facet_id,
                    str(facet.get("label") or facet.get("profile_key") or "已确认的个人理解"),
                    _text(facet.get("value") or ""),
                    updated_at=facet.get("updated_at"),
                    sensitivity="private",
                    data={
                        "domain": facet.get("domain"),
                        "profile_key": facet.get("profile_key"),
                        "value": facet.get("value"),
                        "source": facet.get("source"),
                        "context_enabled": True,
                    },
                )
                facet_item["provenance"] = {
                    "source": "layered_profile",
                    "source_ref": facet_id,
                    "source_hypothesis_id": facet.get("source_hypothesis_id"),
                }
                facet_item["_selection_reason"] = (
                    "你已确认或修正，并允许在当前 AI 上下文中使用。"
                )
                items.append(facet_item)
            return items[:limit]
        if section == "goals":
            goals = self._tasks.list_goals(owner_id, status="active")
            return [
                _item(
                    "goals", "goal", str(goal["goal_id"]), str(goal.get("title")),
                    goal.get("desired_outcome") or goal.get("description") or "Active goal",
                    updated_at=goal.get("updated_at"),
                    data={
                        "status": goal.get("status"), "priority": goal.get("priority"),
                        "run_count": goal.get("run_count", 0),
                        "completed_runs": goal.get("completed_runs", 0),
                    },
                )
                for goal in list(goals)[:limit]
            ]
        if section == "runs":
            runs = [run for run in self._tasks.list_runs(owner_id) if run.get("status") not in {"completed", "cancelled", "failed"}]
            return [
                _item(
                    "runs", "run", str(run["run_id"]), str(run.get("title")),
                    f"{run.get('completed_steps', 0)} of {run.get('step_count', 0)} steps complete",
                    updated_at=run.get("updated_at"),
                    data={
                        "status": run.get("status"), "mode": run.get("mode"),
                        "goal_id": run.get("goal_id"), "goal_title": run.get("goal_title"),
                        "step_count": run.get("step_count", 0),
                        "completed_steps": run.get("completed_steps", 0),
                    },
                )
                for run in runs[:limit]
            ]
        if section == "growth":
            return [
                _item(
                    "growth", "capability", str(capability.get("attr_id")),
                    str(capability.get("attr_name")),
                    f"{capability.get('attr_value', 0)} / {capability.get('max_value', 100)}",
                    updated_at=capability.get("updated_at"),
                    data={
                        "value": capability.get("attr_value", 0),
                        "maximum": capability.get("max_value", 100),
                        "description": _text(capability.get("description")),
                    },
                )
                for capability in list(self._growth.list_capabilities(owner_id))[:limit]
            ]
        if section == "memories":
            eligible_memories = sorted(
                (
                    memory
                    for memory in memories
                    if memory.get("status") == "active"
                    and memory.get("use_in_context", True)
                    and memory.get("review_status", "confirmed") in {"confirmed", "corrected"}
                    and not _is_expired(memory.get("expires_at"))
                ),
                key=_memory_priority,
            )
            items = []
            for memory in eligible_memories[:limit]:
                item = _item(
                    "memories", "memory", str(memory.get("memory_id")),
                    str(memory.get("title")), str(memory.get("content")),
                    updated_at=memory.get("updated_at"),
                    sensitivity="private",
                    data={
                        "memory_type": memory.get("memory_type"),
                        "confidence": memory.get("confidence"),
                        "source_type": memory.get("source_type"),
                        "source_ref": memory.get("source_ref"),
                        "review_status": memory.get("review_status", "confirmed"),
                        "evidence_refs": memory.get("evidence_refs", []),
                        "expires_at": memory.get("expires_at"),
                    },
                )
                item["provenance"]["evidence_refs"] = memory.get("evidence_refs", [])
                item["_selection_reason"] = (
                    "Confirmed memory within the current privacy and freshness policy."
                )
                items.append(item)
            return items
        if section == "knowledge":
            result = self._knowledge.list_documents(owner_id, retention="active", limit=limit, offset=0)
            documents = result.get("documents", []) if isinstance(result, dict) else []
            return [
                _item(
                    "knowledge", "document", str(document.get("doc_id")),
                    str(document.get("title") or document.get("filename") or "Document"),
                    document.get("summary") or document.get("file_type") or "Personal knowledge document",
                    updated_at=document.get("updated_at") or document.get("created_at"),
                    sensitivity="private",
                    data={"status": document.get("parse_status"), "tags": document.get("tags", [])},
                )
                for document in documents
            ]
        if section == "rewards":
            growth_points = self._growth.balance(owner_id)
            return [
                _item(
                    "rewards", "growth_points_summary", owner_id, "Growth points",
                    f"{growth_points} growth points recorded from completed work",
                    data={"growth_points": growth_points},
                )
            ]
        return []
