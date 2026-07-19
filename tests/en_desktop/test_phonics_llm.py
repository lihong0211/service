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
