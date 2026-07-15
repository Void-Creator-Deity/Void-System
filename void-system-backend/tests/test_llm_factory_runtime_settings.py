"""Regression tests for explicitly injected LLM runtime settings."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from core.runtime_settings import RuntimeSettings
from services.ai_services.llm_factory import get_chat_llm, get_embeddings, runtime_settings_scope


class LLMFactoryRuntimeSettingsTests(unittest.TestCase):
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
