# tests/en_desktop/test_phonics_llm.py
"""
DashScope LLM 调用封装测试：mock requests.post，不打真实网络请求
"""
import json

import pytest

from service.en_desktop import phonics_llm


class _FakeResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def _llm_json_response(segments):
    return _FakeResponse(
        200,
        {"choices": [{"message": {"content": json.dumps({"segments": segments})}}]},
    )


def test_request_phonics_segments_success(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "at", "ipa": "æt"}]
    monkeypatch.setattr(
        phonics_llm.requests, "post", lambda *a, **kw: _llm_json_response(segments)
    )

    result = phonics_llm.request_phonics_segments("cat", "/kæt/")
    assert result == segments


def test_request_phonics_segments_uses_thinking_model(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "at", "ipa": "æt"}]
    captured = {}

    def fake_post(*args, **kwargs):
        captured.update(kwargs["json"])
        return _llm_json_response(segments)

    monkeypatch.setattr(phonics_llm.requests, "post", fake_post)
    phonics_llm.request_phonics_segments("cat", "/kæt/")

    assert captured["model"] == phonics_llm.DASHSCOPE_THINKING_MODEL
    assert captured["enable_thinking"] is True


def test_request_phonics_segments_http_error(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(
        phonics_llm.requests, "post", lambda *a, **kw: _FakeResponse(500, {})
    )

    assert phonics_llm.request_phonics_segments("cat", "/kæt/") is None


def test_request_phonics_segments_bad_json_content(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    bad_response = _FakeResponse(200, {"choices": [{"message": {"content": "not json"}}]})
    monkeypatch.setattr(phonics_llm.requests, "post", lambda *a, **kw: bad_response)

    assert phonics_llm.request_phonics_segments("cat", "/kæt/") is None


def test_request_phonics_segments_missing_api_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        phonics_llm.request_phonics_segments("cat", "/kæt/")


def _llm_reasoning_then_json_response(segments):
    """模拟"先写推理过程，最后用 ```json 代码块给答案"的回复格式"""
    content = (
        "推理过程：c->k, at->æt，letters 拼起来是 cat，ipa 拼起来是 kæt，跟音标一致。\n\n"
        "```json\n" + json.dumps({"segments": segments}) + "\n```"
    )
    return _FakeResponse(200, {"choices": [{"message": {"content": content}}]})


def test_request_phonics_segments_parses_fenced_json_after_reasoning(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "at", "ipa": "æt"}]
    monkeypatch.setattr(
        phonics_llm.requests,
        "post",
        lambda *a, **kw: _llm_reasoning_then_json_response(segments),
    )

    assert phonics_llm.request_phonics_segments("cat", "/kæt/") == segments


def test_request_phonics_segments_retries_with_error_feedback_then_succeeds(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    bad_segments = [{"letters": "c", "ipa": "k"}, {"letters": "ot", "ipa": "æt"}]  # letters 错了
    good_segments = [{"letters": "c", "ipa": "k"}, {"letters": "at", "ipa": "æt"}]

    calls = []

    def fake_post(*args, **kwargs):
        calls.append(kwargs["json"]["messages"])
        if len(calls) == 1:
            return _llm_reasoning_then_json_response(bad_segments)
        return _llm_reasoning_then_json_response(good_segments)

    monkeypatch.setattr(phonics_llm.requests, "post", fake_post)

    result = phonics_llm.request_phonics_segments("cat", "/kæt/")
    assert result == good_segments
    assert len(calls) == 2
    # 第二次请求里应该带上第一次的错误反馈，而不是从头再问一遍一模一样的问题
    second_call_messages = calls[1]
    assert any("cot" in m["content"] for m in second_call_messages)


def test_request_phonics_segments_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    always_bad = [{"letters": "x", "ipa": "y"}]
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return _llm_reasoning_then_json_response(always_bad)

    monkeypatch.setattr(phonics_llm.requests, "post", fake_post)

    assert phonics_llm.request_phonics_segments("cat", "/kæt/") is None
    assert len(calls) == phonics_llm.MAX_PHONICS_ATTEMPTS


def test_request_phonics_segments_network_exception_returns_none(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    def _raise(*a, **kw):
        raise phonics_llm.requests.exceptions.ReadTimeout("timed out")

    monkeypatch.setattr(phonics_llm.requests, "post", _raise)
    assert phonics_llm.request_phonics_segments("cat", "/kæt/") is None


def _llm_text_response(text):
    return _FakeResponse(200, {"choices": [{"message": {"content": text}}]})


def test_request_ipa_pronunciation_success(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(
        phonics_llm.requests, "post", lambda *a, **kw: _llm_text_response("/kənˈvɜːrsli/")
    )

    assert phonics_llm.request_ipa_pronunciation("conversely") == "/kənˈvɜːrsli/"


def test_request_ipa_pronunciation_http_error(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(phonics_llm.requests, "post", lambda *a, **kw: _FakeResponse(500, {}))

    assert phonics_llm.request_ipa_pronunciation("conversely") is None


def test_request_ipa_pronunciation_empty_content(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(
        phonics_llm.requests, "post", lambda *a, **kw: _llm_text_response("   ")
    )

    assert phonics_llm.request_ipa_pronunciation("conversely") is None


def test_request_ipa_pronunciation_network_exception_returns_none(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    def _raise(*a, **kw):
        raise phonics_llm.requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr(phonics_llm.requests, "post", _raise)
    assert phonics_llm.request_ipa_pronunciation("conversely") is None
