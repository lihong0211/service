# tests/en_desktop/test_dictionary_pronunciation.py
"""
Free Dictionary API 只取音标（不查释义/不调有道翻译）的测试：mock requests.get
"""
from service.en_desktop import dictionary


class _FakeResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_fetch_pronunciation_picks_uk_and_us_tags(monkeypatch):
    entries = [
        {
            "phonetics": [
                {"text": "/kənˈvɜːsli/", "audio": "...-uk.mp3"},
                {"text": "/kənˈvɜːrsli/", "audio": "...-us.mp3"},
            ]
        }
    ]
    monkeypatch.setattr(
        dictionary.requests, "get", lambda *a, **kw: _FakeResponse(200, entries)
    )

    result = dictionary.fetch_pronunciation("conversely")
    assert result == {
        "en_pronunciation": "/kənˈvɜːsli/",
        "us_pronunciation": "/kənˈvɜːrsli/",
    }


def test_fetch_pronunciation_word_not_found(monkeypatch):
    monkeypatch.setattr(dictionary.requests, "get", lambda *a, **kw: _FakeResponse(404, {}))
    assert dictionary.fetch_pronunciation("zzzznotaword") is None


def test_fetch_pronunciation_empty_entries(monkeypatch):
    monkeypatch.setattr(dictionary.requests, "get", lambda *a, **kw: _FakeResponse(200, []))
    assert dictionary.fetch_pronunciation("zzzznotaword") is None
