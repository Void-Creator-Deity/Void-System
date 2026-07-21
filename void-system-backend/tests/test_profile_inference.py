"""Contract tests for LLM-assisted, review-required profile hypotheses."""
from __future__ import annotations

import json
from types import SimpleNamespace
import unittest

from core.personal_context_contracts import PersonalContextError
from core.runtime_settings import RuntimeSettings
from modules.personal_context.inference import ProfileInference


class CapturingLlm:
    """Small deterministic chat double used to inspect model input and options."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.messages = None
        self.bound_options = {}

    def bind(self, **options):
        self.bound_options = options
        return self

    def invoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content=json.dumps(self.payload, ensure_ascii=False))


class LengthFinishReasonError(Exception):
    """Match the provider exception name used by the service adapter."""


class TruncatedLlm(CapturingLlm):
    def invoke(self, messages):
        self.messages = messages
        raise LengthFinishReasonError()


def _signal(signal_id: str, *, sensitivity: str = "private", status: str = "active") -> dict:
    return {
        "signal_id": signal_id,
        "kind": "task",
        "summary": f"已记录与 {signal_id} 对应的安全汇总执行信息。",
        "observed_at": "2026-07-19T10:00:00+00:00",
        "weight": 0.8,
        "status": status,
        "sensitivity": sensitivity,
    }


class ProfileInferenceTests(unittest.TestCase):
    def test_only_safe_signals_reach_model_and_output_references_signals(self) -> None:
        llm = CapturingLlm({
            "hypotheses": [{
                "domain": "working_style",
                "profile_key": "keeps-next-actions",
                "value": "倾向于在复盘后保留可继续推进的下一步。",
                "summary": "复盘后倾向于留下下一步行动",
                "rationale": "多条已授权的任务汇总记录都显示复盘后保留了后续行动。",
                "confidence": 0.72,
                "evidence_indexes": [0, 2],
            }]
        })
        inference = ProfileInference(
            RuntimeSettings(LLM_PROVIDER="lmstudio", CHAT_MODEL="test-model"),
            llm_factory=lambda **_: llm,
        )
        results = inference.infer(
            [
                _signal("safe-1"),
                _signal("sensitive-1", sensitivity="sensitive"),
                _signal("safe-2"),
                _signal("safe-3"),
                _signal("archived-1", status="archived"),
            ],
            max_hypotheses=3,
        )

        self.assertEqual(llm.bound_options, {"max_tokens": 4096})
        sent = json.loads(llm.messages[1][1])
        self.assertEqual(
            [item["signal_id"] for item in sent["signals"]],
            ["safe-1", "safe-2", "safe-3"],
        )
        self.assertEqual(
            results[0]["evidence_refs"],
            [
                {"type": "profile_signal", "id": "safe-1"},
                {"type": "profile_signal", "id": "safe-3"},
            ],
        )

    def test_invalid_or_generic_model_output_is_rejected(self) -> None:
        llm = CapturingLlm({
            "hypotheses": [{
                "domain": "working_style",
                "profile_key": "generic",
                "value": "建议使用更好的方法。",
                "summary": "建议尝试更好的方法",
                "rationale": "根据记录整理。",
                "confidence": 0.7,
                "evidence_indexes": [0],
            }]
        })
        inference = ProfileInference(RuntimeSettings(), llm_factory=lambda **_: llm)
        with self.assertRaisesRegex(PersonalContextError, "可追溯"):
            inference.infer([_signal("one"), _signal("two"), _signal("three")], max_hypotheses=2)

    def test_fewer_than_three_eligible_signals_are_not_sent_to_model(self) -> None:
        llm = CapturingLlm({"hypotheses": []})
        inference = ProfileInference(RuntimeSettings(), llm_factory=lambda **_: llm)
        with self.assertRaises(PersonalContextError) as raised:
            inference.infer([_signal("one"), _signal("two")], max_hypotheses=2)
        self.assertEqual(raised.exception.code, "PROFILE_INFERENCE_NEEDS_EVIDENCE")
        self.assertIsNone(llm.messages)

    def test_truncated_model_output_has_an_actionable_error(self) -> None:
        llm = TruncatedLlm({})
        inference = ProfileInference(RuntimeSettings(), llm_factory=lambda **_: llm)
        with self.assertRaises(PersonalContextError) as raised:
            inference.infer([_signal("one"), _signal("two"), _signal("three")], max_hypotheses=2)
        self.assertEqual(raised.exception.code, "PROFILE_INFERENCE_OUTPUT_TRUNCATED")


if __name__ == "__main__":
    unittest.main()
