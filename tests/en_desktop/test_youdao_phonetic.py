# tests/en_desktop/test_youdao_phonetic.py
"""
有道词典公开 JSON 接口（dict.youdao.com/jsonapi，跟 en-elctron 客户端放音频用的
dict.youdao.com/dictvoice 是同一个域名下的公开接口，不需要 APP_KEY）取音标的测试。
mock requests.get，不打真实网络请求。
"""
from service.en_desktop import youdao


class _FakeResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_fetch_phonetic_returns_uk_and_us_phone(monkeypatch):
    payload = {
        "ec": {
            "word": [
                {"usphone": "ˈkɑːnvɜːrsli", "ukphone": "ˈkɒnvɜːsli"},
            ]
        }
    }
    monkeypatch.setattr(youdao.requests, "get", lambda *a, **kw: _FakeResponse(200, payload))

    result = youdao.fetch_phonetic("conversely")
    assert result == {"en_pronunciation": "ˈkɒnvɜːsli", "us_pronunciation": "ˈkɑːnvɜːrsli"}


def test_fetch_phonetic_missing_ec_section(monkeypatch):
    monkeypatch.setattr(youdao.requests, "get", lambda *a, **kw: _FakeResponse(200, {}))
    assert youdao.fetch_phonetic("zzzznotaword") is None


def test_fetch_phonetic_empty_word_list(monkeypatch):
    monkeypatch.setattr(
        youdao.requests, "get", lambda *a, **kw: _FakeResponse(200, {"ec": {"word": []}})
    )
    assert youdao.fetch_phonetic("zzzznotaword") is None


def test_fetch_phonetic_missing_phone_fields(monkeypatch):
    payload = {"ec": {"word": [{"return-phrase": {"l": {"i": "conversely"}}}]}}
    monkeypatch.setattr(youdao.requests, "get", lambda *a, **kw: _FakeResponse(200, payload))
    assert youdao.fetch_phonetic("conversely") is None


def test_fetch_phonetic_http_error(monkeypatch):
    monkeypatch.setattr(youdao.requests, "get", lambda *a, **kw: _FakeResponse(500, {}))
    assert youdao.fetch_phonetic("conversely") is None
