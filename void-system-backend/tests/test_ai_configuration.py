"""Tests for the AI connection configuration module."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from modules.administration.ai_configuration import AIConfigurationError, AIConfigurationManager


class FakeConfig:
    LLM_PROVIDER = "ollama"
    EMBEDDING_PROVIDER = "ollama"
    OLLAMA_BASE_URL = "http://localhost:11434"
    CHAT_MODEL = "qwen3"
    EMBEDDING_MODEL = "embed-small"
    OPENAI_BASE_URL = ""
    OPENAI_API_KEY = "stored-openai-key"
    GOOGLE_API_KEY = "stored-google-key"


class FakeRuntimeConfig:
    pass


class FakeProbe:
    def __init__(self) -> None:
        self.calls = []

    def list_ollama_models(self, base_url: str):
        self.calls.append(("ollama", base_url))
        return ["qwen3", "embed-small"]

    def list_openai_models(self, base_url: str, api_key: str):
        self.calls.append(("openai", base_url, api_key))
        return ["gpt-4o-mini", "deepseek-chat", "google/gemma-4-12b-qat"]

    def list_gemini_models(self, api_key: str):
        self.calls.append(("gemini", api_key))
        return ["gemini-2.5-flash"]


class AIConfigurationManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.probe = FakeProbe()
        self.manager = AIConfigurationManager(
            self.env_path,
            FakeConfig,
            FakeRuntimeConfig(),
            self.probe,
        )

    def test_read_profile_only_exposes_ai_configuration(self) -> None:
        self.env_path.write_text(
            "OPENAI_API_KEY=super-secret-value\n"
            "AI_TRACE_LEVEL=debug\n"
            "DEFAULT_ADMIN_PASSWORD=never-return-this\n"
            "SECRET_KEY=also-never-return-this\n",
            encoding="utf-8",
        )

        profile = self.manager.read_profile()

        entries = {row["key"]: row["value"] for row in profile["env_entries"]}
        self.assertEqual({"OPENAI_API_KEY", "AI_TRACE_LEVEL"}, set(entries))
        self.assertNotEqual("super-secret-value", entries["OPENAI_API_KEY"])
        self.assertEqual(["qwen3", "embed-small"], profile["model_options"])

    def test_update_profile_preserves_comments_and_applies_runtime(self) -> None:
        self.env_path.write_text("# local models\nCHAT_MODEL=old\n", encoding="utf-8")

        result = self.manager.update_profile(
            {
                "chat_model": "new model",
                "extra_env": {"AI_TRACE_LEVEL": "verbose"},
                "persist_to_env": True,
                "apply_runtime": True,
            }
        )

        content = self.env_path.read_text(encoding="utf-8")
        self.assertIn("# local models", content)
        self.assertIn('CHAT_MODEL="new model"', content)
        self.assertIn("AI_TRACE_LEVEL=verbose", content)
        self.assertEqual("new model", FakeConfig.CHAT_MODEL)
        self.assertEqual(["AI_TRACE_LEVEL", "CHAT_MODEL"], result["updated_keys"])

    def test_update_rejects_unrelated_environment_keys(self) -> None:
        with self.assertRaises(AIConfigurationError):
            self.manager.update_profile({"extra_env": {"DEFAULT_ADMIN_PASSWORD": "changed"}})

    def test_cloud_probe_uses_stored_secret_when_form_leaves_it_blank(self) -> None:
        result = self.manager.test_profile(
            {
                "llm_provider": "openai",
                "openai_base_url": "https://api.openai.com/v1",
                "chat_model": "gpt-4o-mini",
            }
        )

        self.assertTrue(result["selected_model_available"])
        self.assertEqual(
            ("openai", "https://api.openai.com/v1", "stored-openai-key"),
            self.probe.calls[-1],
        )

    def test_lmstudio_probe_uses_local_placeholder_key(self) -> None:
        result = self.manager.test_profile(
            {
                "llm_provider": "lmstudio",
                "openai_base_url": "http://127.0.0.1:1234/v1",
                "chat_model": "google/gemma-4-12b-qat",
            }
        )

        self.assertTrue(result["selected_model_available"])
        self.assertEqual(
            ("openai", "http://127.0.0.1:1234/v1", "lm-studio"),
            self.probe.calls[-1],
        )

    def test_connection_reports_missing_selected_model(self) -> None:
        with self.assertRaises(AIConfigurationError) as caught:
            self.manager.test_profile(
                {"llm_provider": "ollama", "chat_model": "missing-model"}
            )
        self.assertEqual("AI_MODEL_NOT_FOUND", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
