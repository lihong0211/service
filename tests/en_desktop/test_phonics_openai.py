# tests/en_desktop/test_phonics_openai.py
"""
OpenAI Chat Completions API 拼读拆分测试：mock requests.post，不打真实网络请求。
跟 test_phonics_llm.py 的 DashScope 版本对应，两边接口签名一致方便互换对比。
"""
import json

import pytest

from service.en_desktop import phonics_openai


class _FakeResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def _llm_response(segments):
    return _FakeResponse(
        200,
        {"choices": [{"message": {"content": json.dumps({"segments": segments})}}]},
    )


def test_request_phonics_segments_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "at", "ipa": "æt"}]
    monkeypatch.setattr(phonics_openai.requests, "post", lambda *a, **kw: _llm_response(segments))

    assert phonics_openai.request_phonics_segments("cat", "/kæt/") == segments


def test_request_phonics_segments_uses_structured_output_and_reasoning_effort(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "at", "ipa": "æt"}]
    captured = {}

    def fake_post(*args, **kwargs):
        captured.update(kwargs["json"])
        return _llm_response(segments)

    monkeypatch.setattr(phonics_openai.requests, "post", fake_post)
    phonics_openai.request_phonics_segments("cat", "/kæt/")

    assert captured["model"] == phonics_openai.OPENAI_MODEL
    assert captured["reasoning_effort"] == phonics_openai.OPENAI_REASONING_EFFORT
    assert captured["response_format"]["type"] == "json_schema"


def test_request_phonics_segments_http_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(phonics_openai.requests, "post", lambda *a, **kw: _FakeResponse(500, {}))

    assert phonics_openai.request_phonics_segments("cat", "/kæt/") is None


def test_request_phonics_segments_network_exception_returns_none(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def _raise(*a, **kw):
        raise phonics_openai.requests.exceptions.ReadTimeout("timed out")

    monkeypatch.setattr(phonics_openai.requests, "post", _raise)
    assert phonics_openai.request_phonics_segments("cat", "/kæt/") is None


def test_request_phonics_segments_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        phonics_openai.request_phonics_segments("cat", "/kæt/")


def test_request_phonics_segments_retries_with_error_feedback_then_succeeds(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    bad_segments = [{"letters": "c", "ipa": "k"}, {"letters": "ot", "ipa": "æt"}]
    good_segments = [{"letters": "c", "ipa": "k"}, {"letters": "at", "ipa": "æt"}]
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(kwargs["json"]["messages"])
        if len(calls) == 1:
            return _llm_response(bad_segments)
        return _llm_response(good_segments)

    monkeypatch.setattr(phonics_openai.requests, "post", fake_post)

    result = phonics_openai.request_phonics_segments("cat", "/kæt/")
    assert result == good_segments
    assert len(calls) == 2
    assert any("cot" in m["content"] for m in calls[1])


def test_request_phonics_segments_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    always_bad = [{"letters": "x", "ipa": "y"}]
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return _llm_response(always_bad)

    monkeypatch.setattr(phonics_openai.requests, "post", fake_post)

    assert phonics_openai.request_phonics_segments("cat", "/kæt/") is None
    assert len(calls) == phonics_openai.MAX_PHONICS_ATTEMPTS
