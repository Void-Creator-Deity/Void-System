import asyncio
from types import SimpleNamespace

from api.http.routers import ai as ai_router
from api.http.routers.ai import StreamChatRequest, StreamTextDelta
from api.http.dependencies import get_current_user_optional
from core.knowledge_contracts import KnowledgeChunk, KnowledgeScope
from core.model_connection_profile import ModelConnectionError
from core.runtime_settings import RuntimeSettings
from errors import VoidSystemException
from services.ai_services import persona_chain
from services.ai_services.persona_chain import _persona_instructions


def test_stream_text_delta_converts_cumulative_provider_chunks():
    stream = StreamTextDelta()

    assert stream.consume("Hel") == "Hel"
    assert stream.consume("Hello") == "lo"
    assert stream.consume("Hello, world") == ", world"


def test_stream_text_delta_does_not_replay_a_consumed_chunk():
    stream = StreamTextDelta()

    assert stream.consume("Hello") == "Hello"
    assert stream.consume("Hello") == ""


def test_stream_text_delta_keeps_normal_incremental_chunks():
    stream = StreamTextDelta()

    assert stream.consume("Hel") == "Hel"
    assert stream.consume("lo") == "lo"


def test_persona_instructions_describe_authorized_system_context():
    instructions = _persona_instructions("[runs] Write tests: ready")

    assert "[runs] Write tests: ready" in instructions
    assert "do not claim that you cannot access in-system data" in instructions


def test_persona_instructions_are_honest_when_no_context_is_available():
    instructions = _persona_instructions()

    assert "When the records are empty" in instructions


def test_persona_stream_forwards_authorized_context_for_logged_in_users(monkeypatch):
    captured = {}

    class FakeChain:
        async def astream(self, input_data):
            captured.update(input_data)
            yield "OK"

    class FakeCompanion:
        def build_ai_context(self, owner_id, profile, *, purpose):
            assert owner_id == "user-1"
            assert purpose == "conversation_assist"
            return {"included_sections": ["runs"]}

        def render_ai_context(self, snapshot):
            assert snapshot["included_sections"] == ["runs"]
            return "[runs] Write tests: ready"

    def build_chain(*, settings):
        captured["settings"] = settings
        return FakeChain()

    monkeypatch.setattr(persona_chain, "load_persona_chain", build_chain)
    settings = object()

    async def invoke():
        response = await ai_router.stream_chat_endpoint(
            StreamChatRequest(type="persona", text="What should I do next?"),
            current_user={"user_id": "user-1"},
            attachments=None,
            companion=FakeCompanion(),
            settings=settings,
        )
        async for _chunk in response.body_iterator:
            pass

    asyncio.run(invoke())

    assert captured["personal_context"] == "[runs] Write tests: ready"
    assert captured["text"] == "What should I do next?"
    assert captured["settings"] is settings


def test_persona_stream_retrieves_library_context_only_when_user_allows_it(monkeypatch):
    captured = {}

    class FakeChain:
        async def astream(self, input_data):
            captured.update(input_data)
            yield "OK"

    class FakeCompanion:
        def build_ai_context(self, _owner_id, _profile, *, purpose):
            assert purpose == "conversation_assist"
            return {"included_sections": [], "permissions": {"knowledge": True}}

        def render_ai_context(self, _snapshot):
            return ""

    class FakeEngine:
        def __init__(self):
            self.query = None

        def search(self, query):
            self.query = query
            return [KnowledgeChunk(
                "chunk-1", "document-1", "user-1", "Library evidence for the current question.",
                KnowledgeScope.USER, title="Private note", file_name="note.md",
            )]

    def build_chain(*, settings):
        captured["settings"] = settings
        return FakeChain()

    engine = FakeEngine()
    monkeypatch.setattr(persona_chain, "load_persona_chain", build_chain)

    async def invoke():
        response = await ai_router.stream_chat_endpoint(
            StreamChatRequest(type="persona", text="What did I save about this?"),
            current_user={"user_id": "user-1"},
            attachments=None,
            companion=FakeCompanion(),
            settings=object(),
            resources=SimpleNamespace(engine=engine),
        )
        async for _chunk in response.body_iterator:
            pass

    asyncio.run(invoke())

    assert engine.query is not None
    assert engine.query.owner_id == "user-1"
    assert engine.query.filters == {"include_global_shared": False}
    assert "[knowledge:Private note] Library evidence for the current question." in captured["personal_context"]


def test_persona_stream_does_not_query_library_when_permission_is_off(monkeypatch):
    class FakeChain:
        async def astream(self, _input_data):
            yield "OK"

    class FakeCompanion:
        def build_ai_context(self, _owner_id, _profile, *, purpose):
            assert purpose == "conversation_assist"
            return {"included_sections": [], "permissions": {"knowledge": False}}

        def render_ai_context(self, _snapshot):
            return ""

    class RejectingEngine:
        def search(self, _query):
            raise AssertionError("Library must not be searched without permission")

    monkeypatch.setattr(persona_chain, "load_persona_chain", lambda *, settings: FakeChain())

    async def invoke():
        response = await ai_router.stream_chat_endpoint(
            StreamChatRequest(type="persona", text="What is in my library?"),
            current_user={"user_id": "user-1"},
            attachments=None,
            companion=FakeCompanion(),
            settings=object(),
            resources=SimpleNamespace(engine=RejectingEngine()),
        )
        async for _chunk in response.body_iterator:
            pass

    asyncio.run(invoke())


def test_persona_stream_returns_a_stable_configuration_error(monkeypatch):
    def reject_configuration(*, settings):
        assert settings is not None
        raise ModelConnectionError("Unsupported chat provider.", "AI_PROVIDER_NOT_SUPPORTED")

    monkeypatch.setattr(persona_chain, "load_persona_chain", reject_configuration)

    async def invoke():
        try:
            await ai_router.stream_chat_endpoint(
                StreamChatRequest(type="persona", text="Hello"),
                current_user=None,
                attachments=None,
                companion=None,
                settings=RuntimeSettings(LLM_PROVIDER="unsupported", CHAT_MODEL="test"),
            )
        except VoidSystemException as error:
            return error
        raise AssertionError("Expected a configuration error")

    error = asyncio.run(invoke())

    assert error.status_code == 503
    assert error.error_code == "AI_PROVIDER_NOT_SUPPORTED"


def test_optional_auth_keeps_anonymous_calls_but_rejects_invalid_bearer_tokens():
    class UnusedRepository:
        pass

    settings = RuntimeSettings.from_environment(values={"SECRET_KEY": "test-secret"})

    assert asyncio.run(get_current_user_optional(None, UnusedRepository(), settings)) is None

    try:
        asyncio.run(get_current_user_optional("not-a-valid-token", UnusedRepository(), settings))
    except VoidSystemException as error:
        assert error.status_code == 401
        assert error.error_code == "INVALID_CREDENTIALS"
    else:
        raise AssertionError("A supplied invalid bearer token must be rejected")
