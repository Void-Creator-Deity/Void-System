"""Public, explainable read model for the layered personal understanding workspace."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, Mapping, Sequence


_SOURCE_LABELS = {
    "task_goals:v1": ("目标与方向", "已整理的目标数量"),
    "task_runs:v1": ("执行记录", "执行尝试与完成情况"),
    "task_steps:v1": ("行动拆分", "计划步骤与完成情况"),
    "task_reviews:v1": ("任务复盘", "复盘与后续行动"),
    "task_recovery:v1": ("执行恢复", "暂停、重试与恢复推进"),
    "goal_refinements:v1": ("计划调整", "执行过程中的计划修订"),
}

_FACET_LABELS = {
    "basic": "明确保存的信息",
    "interests": "关注方向",
    "working_style": "工作方式",
    "communication": "协作偏好",
    "values": "判断原则",
    "current_phase": "当前重点",
}


class LayeredProfileWorkspace:
    """Translate canonical profile layers into a calm, user-facing workspace.

    Inputs:
        settings: Owner-controlled profile consent settings.
        profile_view: Canonical signals, patterns, hypotheses, and facets.
    Outputs:
        Public copy with no database identifiers, raw task text, chat content, or
        document content. Only confirmed facets enter the context projection.
    Called by:
        PersonalContext.get_profile_view after deterministic signal refresh.
    """

    def build(
        self, *, settings: Mapping[str, Any], profile_view: Mapping[str, Any]
    ) -> Dict[str, Any]:
        signal_rows = [
            item for item in profile_view.get("signals", [])
            if item.get("status") == "active" and item.get("sensitivity") in {"personal", "private"}
        ]
        signals = [self._public_signal(item) for item in signal_rows]
        signals_by_id = {str(item.get("signal_id")): item for item in signal_rows}
        patterns = [self._public_pattern(item) for item in profile_view.get("patterns", []) if item.get("status") == "active"]
        facets = [self._public_facet(item) for item in profile_view.get("facets", []) if item.get("status") == "active"]
        hypotheses = [
            self._public_hypothesis(item, signals_by_id)
            for item in profile_view.get("hypotheses", [])
            if self._is_presentable_hypothesis(item, signals_by_id)
        ]
        permission_enabled = bool((settings.get("permissions") or {}).get("profile"))
        return {
            "summary": {
                "established": len(facets),
                "reviewing": len(hypotheses),
                "signals": len(signals),
                "patterns": len(patterns),
                "updated_at": self._latest_updated_at(signal_rows, facets, hypotheses),
                "permission_enabled": permission_enabled,
            },
            "facets": facets,
            "patterns": patterns,
            "hypotheses": hypotheses,
            "signals": signals,
            "sources": self._sources(signal_rows),
            "context_projection": {
                "enabled": permission_enabled,
                "facets": [
                    {
                        "label": item["label"],
                        "value": item["context_value"],
                        "source": item["source"],
                    }
                    for item in facets
                    if item["context_enabled"]
                ],
            },
        }

    def _public_signal(self, signal: Mapping[str, Any]) -> Dict[str, Any]:
        source_ref = str(signal.get("source_ref") or "")
        label, category = _SOURCE_LABELS.get(
            source_ref,
            ("明确授权的记录", self._safe_source_label(str(signal.get("source_type") or "manual"))),
        )
        return {
            "label": label,
            "category": category,
            "detail": self._signal_detail(source_ref, signal.get("attributes") or {}),
            "observed_at": signal.get("observed_at") or signal.get("updated_at"),
        }

    def _public_pattern(self, pattern: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "title": self._text(pattern.get("label")),
            "summary": self._text(pattern.get("detail")),
            "freshness": "近期记录",
            "updated_at": pattern.get("updated_at"),
        }

    def _public_facet(self, facet: Mapping[str, Any]) -> Dict[str, Any]:
        """Separate user-facing explanation from the approved value used by AI context."""
        source = "你已确认" if facet.get("source") != "user_corrected" else "你已修正"
        title = self._text(facet.get("label"))
        context_value = self._value_text(facet.get("value"))
        value = context_value
        if title in {"你修正过的理解", "已修正的协作偏好", "已确认的协作偏好"} and context_value:
            title = context_value
            value = "这条协作偏好由你确认后保留，可用于后续协助。"
        return {
            "label": _FACET_LABELS.get(str(facet.get("domain") or ""), "已确认的信息"),
            "title": title,
            "value": value,
            "context_value": context_value,
            "source": source,
            "updated_at": facet.get("updated_at"),
            "context_enabled": bool(facet.get("context_enabled")),
        }

    def _is_presentable_hypothesis(
        self, hypothesis: Mapping[str, Any], signals: Mapping[str, Mapping[str, Any]]
    ) -> bool:
        """Keep malformed or historical candidates out of the public read model.

        A candidate is reviewable only when the current inference contract supplied
        a specific Chinese statement, a reason, and at least one live authorized
        signal. Old claims fail this contract and remain archival data instead.
        """
        if hypothesis.get("status") != "pending":
            return False
        title = self._text(hypothesis.get("summary"))
        rationale = self._text(hypothesis.get("rationale"))
        if not (self._contains_cjk(title) and self._contains_cjk(rationale)):
            return False
        return any(
            isinstance(ref, Mapping) and str(ref.get("id") or "") in signals
            for ref in hypothesis.get("evidence_refs") or []
        )

    def _public_hypothesis(
        self, hypothesis: Mapping[str, Any], signals: Mapping[str, Mapping[str, Any]]
    ) -> Dict[str, Any]:
        evidence = []
        for ref in hypothesis.get("evidence_refs") or []:
            if not isinstance(ref, Mapping):
                continue
            signal = signals.get(str(ref.get("id") or ""))
            if signal is not None:
                public = self._public_signal(signal)
                evidence.append({
                    "label": public["label"], "detail": public["detail"], "observed_at": public["observed_at"],
                })
        return {
            "hypothesis_id": str(hypothesis.get("hypothesis_id") or ""),
            "label": _FACET_LABELS.get(str(hypothesis.get("domain") or ""), "待确认的协作偏好"),
            "title": self._text(hypothesis.get("summary")),
            "detail": self._text(hypothesis.get("rationale")),
            "confidence": float(hypothesis.get("confidence") or 0),
            "evidence": evidence,
            "created_at": hypothesis.get("created_at"),
        }

    def _sources(self, signals: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
        counts = Counter(str(item.get("source_ref") or item.get("source_type") or "manual") for item in signals)
        result: list[Dict[str, Any]] = []
        for key, count in counts.most_common():
            label, detail = _SOURCE_LABELS.get(
                key, ("明确授权的记录", self._safe_source_label(key))
            )
            result.append({
                "label": label, "detail": detail, "count": count,
            })
        return result

    @staticmethod
    def _signal_detail(source_ref: str, attributes: Mapping[str, Any]) -> str:
        if source_ref == "task_goals:v1":
            return f"已记录 {_count(attributes, 'goal_count')} 个目标。"
        if source_ref == "task_runs:v1":
            return f"{_count(attributes, 'run_count')} 次执行尝试，{_count(attributes, 'completed_run_count')} 次完成。"
        if source_ref == "task_steps:v1":
            return f"{_count(attributes, 'step_count')} 个计划步骤，{_count(attributes, 'finished_step_count')} 个已完成或跳过。"
        if source_ref == "task_reviews:v1":
            return f"{_count(attributes, 'review_count')} 次复盘，{_count(attributes, 'review_with_next_action_count')} 次留下后续行动。"
        if source_ref == "task_recovery:v1":
            return f"{_count(attributes, 'pause_count')} 次暂停，{_count(attributes, 'resume_count')} 次恢复，{_count(attributes, 'retry_count')} 次重试。"
        if source_ref == "goal_refinements:v1":
            return f"{_count(attributes, 'goal_plan_refinement_count')} 次计划调整，涉及 {_count(attributes, 'refined_goal_count')} 个目标。"
        return "这条记录已明确授权用于帮助系统理解你的工作方式。"

    @staticmethod
    def _safe_source_label(source_type: str) -> str:
        return {
            "explicit_memory": "你明确授权的长期记忆",
            "profile_hypothesis_review": "你对个人理解的修正",
            "manual": "你主动提供的记录",
        }.get(source_type, "已授权的个人记录")

    @staticmethod
    def _value_text(value: Any) -> str:
        if isinstance(value, str):
            return " ".join(value.split())
        if isinstance(value, Mapping):
            return "；".join(
                f"{LayeredProfileWorkspace._text(key)}：{LayeredProfileWorkspace._text(item)}"
                for key, item in value.items()
            )
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return "；".join(LayeredProfileWorkspace._text(item) for item in value)
        return LayeredProfileWorkspace._text(value)

    @staticmethod
    def _text(value: Any) -> str:
        return " ".join(str(value or "").split())

    @staticmethod
    def _contains_cjk(value: str) -> bool:
        return any("\u4e00" <= char <= "\u9fff" for char in value)

    @staticmethod
    def _latest_updated_at(*collections: Sequence[Mapping[str, Any]]) -> str | None:
        values = [
            str(item.get("updated_at") or item.get("observed_at") or item.get("created_at") or "")
            for collection in collections for item in collection
        ]
        return max(values) if values else None


def _count(values: Mapping[str, Any], key: str) -> int:
    try:
        return max(0, int(values.get(key) or 0))
    except (TypeError, ValueError):
        return 0
