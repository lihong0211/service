"""
有道智云语音合成 (TTS) API 调用测试：mock requests.post，不打真实网络请求
"""
import pytest

from service.en_desktop import youdao


class _FakeResponse:
    def __init__(self, status_code, headers, content=b"", json_data=None, text=""):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


def test_synthesize_speech_success(monkeypatch):
    monkeypatch.setenv("YOUDAO_APP_KEY", "test-key")
    monkeypatch.setenv("YOUDAO_APP_SECRET", "test-secret")
    fake_audio = b"FAKE_MP3_BYTES"
    monkeypatch.setattr(
        youdao.requests,
        "post",
        lambda *a, **kw: _FakeResponse(200, {"Content-Type": "audio/mp3"}, content=fake_audio),
    )

    result = youdao.synthesize_speech("Hello world.")
    assert result == fake_audio


def test_synthesize_speech_error_body_returns_none(monkeypatch):
    monkeypatch.setenv("YOUDAO_APP_KEY", "test-key")
    monkeypatch.setenv("YOUDAO_APP_SECRET", "test-secret")
    monkeypatch.setattr(
        youdao.requests,
        "post",
        lambda *a, **kw: _FakeResponse(
            200,
            {"Content-Type": "application/json"},
            json_data={"errorCode": "110"},
            text='{"errorCode": "110"}',
        ),
    )

    assert youdao.synthesize_speech("Hello world.") is None


def test_synthesize_speech_http_error_returns_none(monkeypatch):
    monkeypatch.setenv("YOUDAO_APP_KEY", "test-key")
    monkeypatch.setenv("YOUDAO_APP_SECRET", "test-secret")
    monkeypatch.setattr(
        youdao.requests, "post", lambda *a, **kw: _FakeResponse(500, {}, text="server error")
    )

    assert youdao.synthesize_speech("Hello world.") is None


def test_synthesize_speech_network_exception_returns_none(monkeypatch):
    monkeypatch.setenv("YOUDAO_APP_KEY", "test-key")
    monkeypatch.setenv("YOUDAO_APP_SECRET", "test-secret")

    def _raise(*a, **kw):
        raise youdao.requests.exceptions.ReadTimeout("timed out")

    monkeypatch.setattr(youdao.requests, "post", _raise)
    assert youdao.synthesize_speech("Hello world.") is None


def test_synthesize_speech_missing_api_key(monkeypatch):
    monkeypatch.delenv("YOUDAO_APP_KEY", raising=False)
    monkeypatch.delenv("YOUDAO_APP_SECRET", raising=False)

    with pytest.raises(RuntimeError):
        youdao.synthesize_speech("Hello world.")
