import asyncio

from langchain_core.messages import AIMessage

from core.runtime_settings import RuntimeSettings
from services.ai_services import persona_chain, vision_caption


def test_persona_chain_captures_the_explicit_runtime_settings(monkeypatch):
    captured = {}

    def build_llm(**kwargs):
        captured.update(kwargs)
        return lambda _value: "unused"

    monkeypatch.setattr(persona_chain, "get_chat_llm", build_llm)
    settings = RuntimeSettings(LLM_PROVIDER="lmstudio", CHAT_MODEL="chat-model")

    persona_chain.load_persona_chain(settings=settings)

    assert captured["settings"] is settings
    assert captured["temperature"] == 0.5


def test_image_caption_uses_the_explicit_runtime_settings(monkeypatch):
    captured = {}

    class FakeLlm:
        async def ainvoke(self, _messages):
            return AIMessage(content="A concise image summary.")

    def build_llm(**kwargs):
        captured.update(kwargs)
        return FakeLlm()

    monkeypatch.setattr(vision_caption, "get_chat_llm", build_llm)
    settings = RuntimeSettings(LLM_PROVIDER="lmstudio", CHAT_MODEL="vision-model")

    result = asyncio.run(
        vision_caption.caption_one_image_data_url(
            "data:image/png;base64,AA==",
            settings=settings,
        )
    )

    assert result == "A concise image summary."
    assert captured["settings"] is settings
    assert captured["temperature"] == 0.2
