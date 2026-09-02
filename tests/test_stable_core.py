import math

from core.ai import (
    BACKEND_DEEPSEEK,
    BACKEND_ORCAROUTER,
    BACKEND_OPENAI,
    chat,
    parse_classification,
    resolve_api_key,
)
from core.simulation import glacier_surface_melt_pressure
from core.universe import match_topic


TOPICS = [
    "Antarctic Ice Sheet",
    "CDW Intrusion",
    "Ice-shelf Basal Melt",
    "Grounding Line Retreat",
    "GRACE / GRACE-FO",
]
KEYWORDS = {
    "CDW Intrusion": ["cdw", "circumpolar deep water"],
    "Ice-shelf Basal Melt": ["basal melt", "ice shelf melt"],
    "Grounding Line Retreat": ["grounding line", "retreat"],
    "GRACE / GRACE-FO": ["grace", "gravity"],
}


def test_api_keys_are_scoped_to_the_selected_provider():
    assert resolve_api_key(
        BACKEND_OPENAI,
        typed_backend=BACKEND_DEEPSEEK,
        typed_key="deep-key",
        environ={},
    ) == ""
    assert resolve_api_key(
        BACKEND_OPENAI,
        typed_backend=BACKEND_OPENAI,
        typed_key="openai-key",
        session_keys={BACKEND_DEEPSEEK: "deep-key"},
        environ={},
    ) == "openai-key"


def test_api_keys_fall_back_only_within_the_provider():
    keys = {BACKEND_DEEPSEEK: "deep-session", BACKEND_OPENAI: "open-session"}
    assert resolve_api_key(BACKEND_DEEPSEEK, session_keys=keys, environ={}) == "deep-session"
    assert resolve_api_key(BACKEND_OPENAI, session_keys=keys, environ={}) == "open-session"
    assert resolve_api_key(BACKEND_OPENAI, session_keys={}, environ={"OPENAI_API_KEY": "open-env"}) == "open-env"


def test_orcarouter_key_is_provider_scoped_and_reads_its_environment_name():
    assert resolve_api_key(
        BACKEND_ORCAROUTER,
        typed_backend=BACKEND_OPENAI,
        typed_key="open-key",
        session_keys={BACKEND_OPENAI: "open-session"},
        environ={"ORCAROUTER_API_KEY": "orca-env"},
    ) == "orca-env"
    assert resolve_api_key(
        BACKEND_ORCAROUTER,
        typed_backend=BACKEND_ORCAROUTER,
        typed_key="orca-typed",
        environ={"ORCAROUTER_API_KEY": "orca-env"},
    ) == "orca-typed"


def test_orcarouter_chat_uses_openai_compatible_endpoint(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200
        text = ""

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def json(self):
            return {"choices": [{"message": {"content": "connection-ok"}}]}

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("core.ai.requests.post", fake_post)
    assert chat(BACKEND_ORCAROUTER, "Reply", api_key="orca-test-key") == "connection-ok"

    url, kwargs = calls[0]
    assert url == "https://api.orcarouter.ai/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer orca-test-key"
    assert kwargs["json"]["model"] == "gpt-4o"
    assert kwargs["json"]["messages"][-1] == {"role": "user", "content": "Reply"}
    assert kwargs["json"]["stream"] is False


def test_orcarouter_streaming_chat_forwards_sse_chunks(monkeypatch):
    chunks = []

    class FakeResponse:
        status_code = 200
        text = ""

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def iter_lines(self, decode_unicode=True):
            assert decode_unicode is True
            return iter([
                'data: {"choices":[{"delta":{"content":"con"}}]}',
                'data: {"choices":[{"delta":{"content":"nection-ok"}}]}',
                "data: [DONE]",
            ])

    monkeypatch.setattr("core.ai.requests.post", lambda *_args, **_kwargs: FakeResponse())
    result = chat(
        BACKEND_ORCAROUTER,
        "Reply",
        api_key="orca-test-key",
        on_chunk=chunks.append,
    )

    assert result == "connection-ok"
    assert chunks == ["con", "nection-ok"]


def test_classification_confidence_is_finite_and_bounded():
    assert parse_classification('{"topic":"CDW Intrusion","confidence":83}') == ("CDW Intrusion", 0.83)
    assert parse_classification('{"topic":"CDW Intrusion","confidence":900}')[1] == 1.0
    assert parse_classification('{"topic":"CDW Intrusion","confidence":"nan"}')[1] == 0.0
    assert math.isfinite(parse_classification('{"topic":"CDW Intrusion","confidence":"nan"}')[1])


def test_chinese_topic_matching_reaches_leaf_nodes():
    assert match_topic("接地线后退为什么重要？", TOPICS, topic_keywords=KEYWORDS)[0] == "Grounding Line Retreat"
    assert match_topic("冰架基底融化有什么影响？", TOPICS, topic_keywords=KEYWORDS)[0] == "Ice-shelf Basal Melt"
    assert match_topic("环南极深层水如何影响冰盖？", TOPICS, topic_keywords=KEYWORDS)[0] == "CDW Intrusion"
    assert match_topic("GRACE 能测量什么？", TOPICS, topic_keywords=KEYWORDS)[0] == "GRACE / GRACE-FO"


def test_english_topic_matching_regression():
    assert match_topic("Why is grounding line retreat important?", TOPICS, topic_keywords=KEYWORDS)[0] == "Grounding Line Retreat"


def test_surface_melt_pressure_increases_with_warming():
    values = [glacier_surface_melt_pressure(value) for value in (-5.0, -2.0, 0.0)]
    assert values == sorted(values)
    assert values[0] == 0.0
    assert values[-1] > values[0]
