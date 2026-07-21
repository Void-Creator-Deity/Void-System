"""LLM-assisted, review-required profile hypothesis inference."""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Mapping, Sequence

from core.personal_context_contracts import PersonalContextError
from core.runtime_settings import RuntimeSettings
from modules.personal_context.profile import PROFILE_DOMAINS
from services.ai_services.llm_factory import chat_output_limit_options, get_chat_llm


MINIMUM_PROFILE_EVIDENCE = 3
_MAX_TEXT = {"profile_key": 160, "value": 500, "summary": 240, "rationale": 1000}
_CODE_FENCE = re.compile(r"^\`\`\`(?:json)?\s*(.*?)\s*\`\`\`$", re.DOTALL | re.IGNORECASE)


class ProfileInference:
    """Organize safe signals into review-required hypotheses, never effective facts.

    Inputs:
        Active profile signals with a stable identifier, safe summary, and factual
        aggregate metadata. Callers must remove task titles, note bodies, document
        text, conversation text, and other arbitrary user content before invocation.
    Outputs:
        Validated hypothesis payloads. They are not persisted or injected into AI
        context here; the caller persists them for explicit user review.
    Called by:
        PersonalContext.infer_profile_hypotheses after consent and evidence checks.
    """

    def __init__(
        self,
        settings: RuntimeSettings,
        llm_factory: Callable[..., Any] = get_chat_llm,
    ) -> None:
        self._settings = settings
        self._llm_factory = llm_factory

    @property
    def model_name(self) -> str:
        """Return the configured chat model name for capability diagnostics."""
        return str(self._settings.CHAT_MODEL or "").strip()

    def infer(
        self,
        signals: Sequence[Mapping[str, Any]],
        *,
        max_hypotheses: int,
    ) -> Sequence[Dict[str, Any]]:
        """Invoke the configured model and validate review-required hypotheses.

        Input:
            signals: Canonical active profile signals selected by the service.
            max_hypotheses: Bounded number of model outputs to accept.
        Output:
            Normalized hypothesis payloads with references to canonical signal IDs.
        Raises:
            PersonalContextError when the evidence is insufficient, the provider is
            unavailable, or its output fails the strict product contract.
        """
        evidence = self._safe_evidence(signals)
        if len(evidence) < MINIMUM_PROFILE_EVIDENCE:
            raise PersonalContextError(
                "至少需要 3 条适合的已授权依据，才能整理待确认的个人理解。",
                "PROFILE_INFERENCE_NEEDS_EVIDENCE",
                422,
            )
        llm = self._llm_factory(
            temperature=0.1,
            json_mode=True,
            settings=self._settings,
        )
        if hasattr(llm, "bind"):
            llm = llm.bind(**self._invocation_options())
        try:
            response = llm.invoke([
                ("system", self._system_prompt(max_hypotheses)),
                ("human", json.dumps({"signals": evidence}, ensure_ascii=False)),
            ])
        except Exception as exc:
            if type(exc).__name__ == "LengthFinishReasonError":
                raise PersonalContextError(
                    "模型已开始整理候选理解，但本次输出未完成。请调高模型输出上限后重试。",
                    "PROFILE_INFERENCE_OUTPUT_TRUNCATED",
                    422,
                ) from exc
            upstream_status = getattr(exc, "status_code", None)
            if isinstance(upstream_status, int):
                raise PersonalContextError(
                    f"AI 上游服务返回 HTTP {upstream_status}，尚未生成候选理解。请检查模型服务后重试。",
                    "PROFILE_INFERENCE_UPSTREAM_ERROR",
                    502,
                ) from exc
            raise PersonalContextError(
                "AI 服务暂时无法整理候选理解。请检查连接和已加载模型后重试。",
                "PROFILE_INFERENCE_MODEL_FAILED",
                502,
            ) from exc
        return self._validate_output(
            self._response_text(response), evidence, max_hypotheses
        )

    def _invocation_options(self) -> Dict[str, Any]:
        """Return a bounded output budget while leaving transport choices to the LLM factory."""
        return chat_output_limit_options(max_tokens=4096, settings=self._settings)

    def _safe_evidence(self, signals: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
        """Select the minimal factual signal fields that may be sent to the model."""
        result: list[Dict[str, Any]] = []
        for signal in signals:
            if signal.get("status") != "active":
                continue
            if signal.get("sensitivity") not in {"personal", "private"}:
                continue
            summary = " ".join(str(signal.get("summary") or "").split())
            signal_id = str(signal.get("signal_id") or "").strip()
            if not summary or not signal_id:
                continue
            result.append({
                "index": len(result),
                "signal_id": signal_id,
                "kind": str(signal.get("kind") or "manual"),
                "summary": summary[:500],
                "observed_at": signal.get("observed_at") or signal.get("created_at"),
                "weight": signal.get("weight", 1.0),
            })
        return result

    @staticmethod
    def _system_prompt(max_hypotheses: int) -> str:
        return f"""你正在整理“待用户确认的工作方式理解”，不是给用户贴人格标签。
只返回 JSON，严格使用此结构：{{"hypotheses":[{{"domain":"working_style","profile_key":"short-key","value":"...","summary":"...","rationale":"...","confidence":0.0,"evidence_indexes":[0]}}]}}。
最多生成 {max_hypotheses} 条，只能使用这些 domain：{', '.join(PROFILE_DOMAINS)}。
所有 value、summary、rationale 必须是简体中文；profile_key 使用简短 ASCII kebab-case。每条都必须明确引用至少一条输入 evidence_indexes；有多个独立依据时优先引用两个以上。
summary 必须是具体、可被用户确认或修正的一句话，例如“复盘后倾向于留下下一步行动”，不得是泛泛建议、模型自我介绍、免责声明或“可能有帮助”之类的空话。rationale 要说明记录到的具体行为，不要复述 summary。
只根据提供的汇总记录描述工作与协作偏好。不得推断敏感特征、诊断、身份、受保护属性、情绪、人生阶段或固定人格；不得因为取消、暂停或未完成而给出负面评价。不要输出思维过程，也不要输出 JSON 之外的字段。"""

    @staticmethod
    def _response_text(response: Any) -> str:
        """Extract plain text from provider response shapes without trusting extra fields."""
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(
                str(item.get("text") or "") if isinstance(item, Mapping) else str(item)
                for item in content
            )
        text = str(content or "").strip()
        match = _CODE_FENCE.match(text)
        return match.group(1).strip() if match else text

    def _validate_output(
        self,
        raw: str,
        evidence: Sequence[Mapping[str, Any]],
        max_hypotheses: int,
    ) -> Sequence[Dict[str, Any]]:
        """Reject malformed, generic, non-Chinese, or ungrounded model output."""
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise PersonalContextError(
                "AI 返回的画像候选格式无效。",
                "PROFILE_INFERENCE_INVALID_OUTPUT",
                422,
            ) from exc
        hypotheses = payload.get("hypotheses") if isinstance(payload, Mapping) else None
        if not isinstance(hypotheses, list):
            raise PersonalContextError(
                "AI 返回的画像候选格式无效。",
                "PROFILE_INFERENCE_INVALID_OUTPUT",
                422,
            )
        valid_indexes = {int(item["index"]) for item in evidence}
        normalized: list[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for candidate in hypotheses[:max_hypotheses]:
            if not isinstance(candidate, Mapping):
                continue
            try:
                domain = str(candidate.get("domain") or "").strip()
                profile_key = self._text(candidate.get("profile_key"), "profile_key")
                value = self._text(candidate.get("value"), "value")
                summary = self._text(candidate.get("summary"), "summary")
                rationale = self._text(candidate.get("rationale"), "rationale")
                confidence = round(float(candidate.get("confidence")), 4)
                indexes = candidate.get("evidence_indexes")
                if domain not in PROFILE_DOMAINS or not 0 <= confidence <= 1:
                    continue
                if not _contains_cjk(value) or not _contains_cjk(summary) or not _contains_cjk(rationale):
                    continue
                if _is_generic_hypothesis(summary):
                    continue
                if not isinstance(indexes, list):
                    continue
                indexes = sorted({int(index) for index in indexes})
                if not indexes or any(index not in valid_indexes for index in indexes):
                    continue
                key = (domain, profile_key)
                if key in seen:
                    continue
                seen.add(key)
                normalized.append({
                    "domain": domain,
                    "profile_key": profile_key,
                    "value": value,
                    "summary": summary,
                    "rationale": rationale,
                    "confidence": confidence,
                    "evidence_refs": [
                        {"type": "profile_signal", "id": evidence[index]["signal_id"]}
                        for index in indexes
                    ],
                })
            except (TypeError, ValueError, KeyError):
                continue
        if hypotheses and not normalized:
            raise PersonalContextError(
                "AI 没有返回可追溯、可确认的候选理解。",
                "PROFILE_INFERENCE_INVALID_OUTPUT",
                422,
            )
        return normalized

    @staticmethod
    def _text(value: Any, field: str) -> str:
        text = " ".join(str(value or "").split())
        if not text or len(text) > _MAX_TEXT[field]:
            raise ValueError(field)
        return text


def _contains_cjk(value: str) -> bool:
    """Return whether a user-visible model field contains Chinese characters."""
    return any("\u4e00" <= character <= "\u9fff" for character in value)


def _is_generic_hypothesis(value: str) -> bool:
    """Reject advice-shaped placeholders rather than evidence-grounded understandings."""
    normalized = "".join(value.split()).lower()
    blocked = ("maybenefit", "建议", "请提供", "已就绪", "根据您的指令")
    return any(item in normalized for item in blocked)
