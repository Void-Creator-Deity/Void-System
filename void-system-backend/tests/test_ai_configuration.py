"""Tests for the AI connection configuration module."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dotenv import dotenv_values

from core.runtime_settings import RuntimeSettings
from modules.administration.ai_configuration import AIConfigurationError, AIConfigurationManager


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


    def verify_ollama_chat(self, base_url: str, model: str):
        self.calls.append(("ollama-chat", base_url, model))

    def verify_openai_chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        local: bool = False,
        request_body_options=None,
    ):
        self.calls.append(("openai-chat", base_url, api_key, model, local, request_body_options))

class AIConfigurationManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.probe = FakeProbe()
        self.runtime = RuntimeSettings(
            LLM_PROVIDER="ollama",
            EMBEDDING_PROVIDER="ollama",
            OLLAMA_BASE_URL="http://localhost:11434",
            CHAT_MODEL="qwen3",
            EMBEDDING_MODEL="embed-small",
            OPENAI_API_KEY="stored-openai-key",
            GOOGLE_API_KEY="stored-google-key",
        )
        self.manager = AIConfigurationManager(
            self.env_path,
            self.runtime,
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
        self.assertEqual([], profile["model_options"])
        self.assertTrue(profile["openai_api_key_set"])
        self.assertEqual([], self.probe.calls)

    def test_saved_profile_survives_a_fresh_runtime_settings_load(self) -> None:
        self.manager.update_profile(
            {
                "llm_provider": "openai",
                "embedding_provider": "ollama",
                "openai_base_url": "https://example.invalid/v1",
                "openai_api_key": "persisted-test-key",
                "chat_model": "gpt-5.6-luna",
                "embedding_model": "qwen3-embedding",
                "persist_to_env": True,
                "apply_runtime": True,
            }
        )

        persisted_values = {
            key: value
            for key, value in dotenv_values(self.env_path).items()
            if value is not None
        }
        restarted_runtime = RuntimeSettings.from_environment(persisted_values)
        restarted_manager = AIConfigurationManager(self.env_path, restarted_runtime, self.probe)

        profile = restarted_manager.read_profile()

        self.assertEqual("openai", profile["llm_provider"])
        self.assertEqual("gpt-5.6-luna", profile["chat_model"])
        self.assertEqual("https://example.invalid/v1", profile["openai_base_url"])
        self.assertEqual("qwen3-embedding", profile["embedding_model"])
        self.assertTrue(profile["openai_api_key_set"])
        self.assertEqual([], self.probe.calls)

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
        self.assertEqual("new model", self.manager.runtime_config.CHAT_MODEL)
        self.assertEqual(["AI_TRACE_LEVEL", "CHAT_MODEL"], result["updated_keys"])

    def test_runtime_update_publishes_a_new_settings_snapshot(self) -> None:
        previous = RuntimeSettings(CHAT_MODEL="before", LLM_PROVIDER="ollama")
        published = []
        manager = AIConfigurationManager(
            self.env_path,
            previous,
            self.probe,
            runtime_update_callback=published.append,
        )

        manager.update_profile(
            {"chat_model": "after", "persist_to_env": False, "apply_runtime": True}
        )

        self.assertEqual("before", previous.CHAT_MODEL)
        self.assertEqual("after", manager.runtime_config.CHAT_MODEL)
        self.assertIsNot(previous, manager.runtime_config)
        self.assertEqual("after", published[0].CHAT_MODEL)


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
        self.assertTrue(result["chat_generation_verified"])
        self.assertEqual(
            ("openai-chat", "https://api.openai.com/v1", "stored-openai-key", "gpt-4o-mini", False, {}),
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
        self.assertTrue(result["chat_generation_verified"])
        self.assertEqual(
            ("openai-chat", "http://127.0.0.1:1234/v1", "lm-studio", "google/gemma-4-12b-qat", True, {"chat_template_kwargs": {"enable_thinking": False}}),
            self.probe.calls[-1],
        )

    def test_lmstudio_probe_normalizes_the_local_server_root(self) -> None:
        self.manager.test_profile(
            {
                "llm_provider": "lmstudio",
                "openai_base_url": "http://127.0.0.1:1234",
                "chat_model": "google/gemma-4-12b-qat",
            }
        )

        self.assertEqual(
            ("openai-chat", "http://127.0.0.1:1234/v1", "lm-studio", "google/gemma-4-12b-qat", True, {"chat_template_kwargs": {"enable_thinking": False}}),
            self.probe.calls[-1],
        )

    def test_selecting_lmstudio_persists_the_local_openai_endpoint(self) -> None:
        result = self.manager.update_profile(
            {"llm_provider": "lmstudio", "persist_to_env": True, "apply_runtime": True}
        )

        self.assertEqual("lmstudio", self.manager.runtime_config.LLM_PROVIDER)
        self.assertEqual("http://127.0.0.1:1234/v1", self.manager.runtime_config.OPENAI_BASE_URL)
        self.assertIn("OPENAI_BASE_URL", result["updated_keys"])

    def test_model_discovery_only_lists_upstream_models(self) -> None:
        result = self.manager.discover_models(
            {
                "llm_provider": "lmstudio",
                "openai_base_url": "http://127.0.0.1:1234",
            }
        )

        self.assertEqual("lmstudio", result["provider"])
        self.assertEqual(3, result["model_count"])
        self.assertIn("google/gemma-4-12b-qat", result["model_options"])
        self.assertEqual(("openai", "http://127.0.0.1:1234/v1", "lm-studio"), self.probe.calls[-1])

    def test_connection_reports_missing_selected_model(self) -> None:
        with self.assertRaises(AIConfigurationError) as caught:
            self.manager.test_profile(
                {"llm_provider": "ollama", "chat_model": "missing-model"}
            )
        self.assertEqual("AI_MODEL_NOT_FOUND", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
