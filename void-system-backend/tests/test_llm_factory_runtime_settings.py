"""Regression tests for explicitly injected LLM runtime settings."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from core.runtime_settings import RuntimeSettings
from core.model_connection_profile import ModelConnectionError
from services.ai_services.llm_factory import (
    chat_output_limit_options,
    get_chat_llm,
    get_embeddings,
    runtime_settings_scope,
)


class LLMFactoryRuntimeSettingsTests(unittest.TestCase):
    def test_output_limit_uses_the_resolved_chat_protocol(self) -> None:
        ollama = RuntimeSettings(LLM_PROVIDER="ollama", CHAT_MODEL="qwen3")
        lmstudio = RuntimeSettings(LLM_PROVIDER="lmstudio", CHAT_MODEL="local-model")
        gemini = RuntimeSettings(
            LLM_PROVIDER="gemini", CHAT_MODEL="gemini-2.5-flash", GOOGLE_API_KEY="test-key"
        )

        self.assertEqual(
            {"num_predict": 512}, chat_output_limit_options(max_tokens=512, settings=ollama)
        )
        self.assertEqual(
            {"max_tokens": 512}, chat_output_limit_options(max_tokens=512, settings=lmstudio)
        )
        self.assertEqual(
            {"max_output_tokens": 512},
            chat_output_limit_options(max_tokens=512, settings=gemini),
        )
    def test_openai_uses_the_configured_custom_endpoint(self) -> None:
        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_module = types.ModuleType("langchain_openai")
        fake_module.ChatOpenAI = FakeChatOpenAI
        settings = RuntimeSettings(
            LLM_PROVIDER="openai",
            CHAT_MODEL="gpt-4.1-mini",
            OPENAI_API_KEY="test-key",
            OPENAI_BASE_URL="https://gateway.example.test/v1",
        )

        with patch.dict(sys.modules, {"langchain_openai": fake_module}):
            chat = get_chat_llm(temperature=0.1, settings=settings)

        self.assertEqual("gpt-4.1-mini", chat.kwargs["model"])
        self.assertEqual("https://gateway.example.test/v1", chat.kwargs["base_url"])
        self.assertFalse(chat.kwargs["use_responses_api"])
        self.assertTrue(chat.kwargs["streaming"])

    def test_compatible_gateway_uses_prompt_enforced_json_without_response_format(self) -> None:
        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_module = types.ModuleType("langchain_openai")
        fake_module.ChatOpenAI = FakeChatOpenAI
        settings = RuntimeSettings(
            LLM_PROVIDER="openai",
            CHAT_MODEL="gpt-5.6-luna",
            OPENAI_API_KEY="test-key",
            OPENAI_BASE_URL="https://gateway.example.test/v1",
        )

        with patch.dict(sys.modules, {"langchain_openai": fake_module}):
            chat = get_chat_llm(json_mode=True, streaming=False, settings=settings)

        self.assertFalse(chat.kwargs["streaming"])
        self.assertNotIn("model_kwargs", chat.kwargs)

    def test_official_openai_endpoint_keeps_responses_api_available(self) -> None:
        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_module = types.ModuleType("langchain_openai")
        fake_module.ChatOpenAI = FakeChatOpenAI
        settings = RuntimeSettings(
            LLM_PROVIDER="openai",
            CHAT_MODEL="gpt-5.6-luna",
            OPENAI_API_KEY="test-key",
            OPENAI_BASE_URL="https://api.openai.com/v1",
        )

        with patch.dict(sys.modules, {"langchain_openai": fake_module}):
            chat = get_chat_llm(settings=settings)

        self.assertNotIn("use_responses_api", chat.kwargs)
        self.assertNotIn("streaming", chat.kwargs)

    def test_injected_settings_override_global_model_configuration(self) -> None:
        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeOpenAIEmbeddings:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_module = types.ModuleType("langchain_openai")
        fake_module.ChatOpenAI = FakeChatOpenAI
        fake_module.OpenAIEmbeddings = FakeOpenAIEmbeddings
        settings = RuntimeSettings(
            LLM_PROVIDER="openai_compat",
            CHAT_MODEL="google/gemma-4-12b-qat",
            OPENAI_API_KEY="test-key",
            OPENAI_BASE_URL="http://127.0.0.1:1234/v1",
            EMBEDDING_PROVIDER="openai",
            EMBEDDING_MODEL="test-embedding-model",
        )

        with patch.dict(sys.modules, {"langchain_openai": fake_module}):
            chat = get_chat_llm(temperature=0.1, settings=settings)
            embeddings = get_embeddings(settings=settings)

        self.assertEqual("google/gemma-4-12b-qat", chat.kwargs["model"])
        self.assertEqual("http://127.0.0.1:1234/v1", chat.kwargs["base_url"])
        self.assertEqual("test-embedding-model", embeddings.kwargs["model"])
        self.assertEqual("http://127.0.0.1:1234/v1", embeddings.kwargs["base_url"])


    def test_lmstudio_uses_local_defaults_without_a_cloud_secret(self) -> None:
        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_module = types.ModuleType("langchain_openai")
        fake_module.ChatOpenAI = FakeChatOpenAI
        settings = RuntimeSettings(
            LLM_PROVIDER="lmstudio",
            CHAT_MODEL="google/gemma-4-12b-qat",
        )

        with patch.dict(sys.modules, {"langchain_openai": fake_module}):
            chat = get_chat_llm(temperature=0.0, settings=settings)

        self.assertEqual("google/gemma-4-12b-qat", chat.kwargs["model"])
        self.assertEqual("http://127.0.0.1:1234/v1", chat.kwargs["base_url"])
        self.assertEqual("lm-studio", chat.kwargs["api_key"])
        self.assertEqual(
            {"chat_template_kwargs": {"enable_thinking": False}},
            chat.kwargs["extra_body"],
        )

    def test_unknown_provider_fails_instead_of_falling_back_to_ollama(self) -> None:
        settings = RuntimeSettings(LLM_PROVIDER="unknown-provider", CHAT_MODEL="unused")

        with self.assertRaises(ModelConnectionError) as caught:
            get_chat_llm(settings=settings)

        self.assertEqual("AI_PROVIDER_NOT_SUPPORTED", caught.exception.code)

    def test_scoped_settings_apply_to_embeddings_without_explicit_argument(self) -> None:
        class FakeOpenAIEmbeddings:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_module = types.ModuleType("langchain_openai")
        fake_module.OpenAIEmbeddings = FakeOpenAIEmbeddings
        settings = RuntimeSettings(
            EMBEDDING_PROVIDER="openai",
            EMBEDDING_MODEL="scoped-embedding-model",
            OPENAI_API_KEY="test-key",
            OPENAI_BASE_URL="http://127.0.0.1:1234/v1",
        )

        with patch.dict(sys.modules, {"langchain_openai": fake_module}):
            with runtime_settings_scope(settings):
                embeddings = get_embeddings()

        self.assertEqual("scoped-embedding-model", embeddings.kwargs["model"])
        self.assertEqual("http://127.0.0.1:1234/v1", embeddings.kwargs["base_url"])


if __name__ == "__main__":
    unittest.main()
