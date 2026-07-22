"""
腾讯云语音合成 (TextToVoice) API 调用测试：mock requests.post，不打真实网络请求
"""
import base64

import pytest

from service.en_desktop import tencent_tts


class _FakeResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_synthesize_speech_success(monkeypatch):
    monkeypatch.setenv("TENCENTCLOUD_SECRET_ID", "test-id")
    monkeypatch.setenv("TENCENTCLOUD_SECRET_KEY", "test-key")
    fake_audio = b"FAKE_MP3_BYTES"
    encoded = base64.b64encode(fake_audio).decode("ascii")
    monkeypatch.setattr(
        tencent_tts.requests,
        "post",
        lambda *a, **kw: _FakeResponse(200, {"Response": {"Audio": encoded, "RequestId": "r1"}}),
    )

    result = tencent_tts.synthesize_speech("Hello world.")
    assert result == fake_audio


def test_synthesize_speech_error_response_returns_none(monkeypatch):
    monkeypatch.setenv("TENCENTCLOUD_SECRET_ID", "test-id")
    monkeypatch.setenv("TENCENTCLOUD_SECRET_KEY", "test-key")
    monkeypatch.setattr(
        tencent_tts.requests,
        "post",
        lambda *a, **kw: _FakeResponse(
            200,
            {
                "Response": {
                    "Error": {"Code": "FailedOperation", "Message": "quota exceeded"},
                    "RequestId": "r2",
                }
            },
        ),
    )

    assert tencent_tts.synthesize_speech("Hello world.") is None


def test_synthesize_speech_http_error_returns_none(monkeypatch):
    monkeypatch.setenv("TENCENTCLOUD_SECRET_ID", "test-id")
    monkeypatch.setenv("TENCENTCLOUD_SECRET_KEY", "test-key")
    monkeypatch.setattr(
        tencent_tts.requests, "post", lambda *a, **kw: _FakeResponse(500, {})
    )

    assert tencent_tts.synthesize_speech("Hello world.") is None


def test_synthesize_speech_network_exception_returns_none(monkeypatch):
    monkeypatch.setenv("TENCENTCLOUD_SECRET_ID", "test-id")
    monkeypatch.setenv("TENCENTCLOUD_SECRET_KEY", "test-key")

    def _raise(*a, **kw):
        raise tencent_tts.requests.exceptions.ReadTimeout("timed out")

    monkeypatch.setattr(tencent_tts.requests, "post", _raise)
    assert tencent_tts.synthesize_speech("Hello world.") is None


def test_synthesize_speech_missing_credentials(monkeypatch):
    monkeypatch.delenv("TENCENTCLOUD_SECRET_ID", raising=False)
    monkeypatch.delenv("TENCENTCLOUD_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError):
        tencent_tts.synthesize_speech("Hello world.")
