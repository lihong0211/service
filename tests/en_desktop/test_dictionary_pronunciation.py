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


def test_lookup_word_falls_back_to_llm_when_dictionary_has_no_text_phonetic(monkeypatch):
    """词典只有音频没有文本音标（兜底成 "-"）时，当场用 LLM 补，不留占位符"""
    entries = [
        {
            "phonetics": [{"audio": "https://.../preload-au.mp3"}],
            "meanings": [
                {
                    "partOfSpeech": "verb",
                    "definitions": [{"definition": "to load in advance"}],
                }
            ],
        }
    ]
    monkeypatch.setattr(
        dictionary.requests, "get", lambda *a, **kw: _FakeResponse(200, entries)
    )
    monkeypatch.setattr(dictionary, "translate_to_chinese", lambda text: "预先装入")
    monkeypatch.setattr(dictionary, "request_ipa_pronunciation", lambda word: "/ˈpriːloʊd/")

    result = dictionary.lookup_word("preload")
    assert result["en_pronunciation"] == "/ˈpriːloʊd/"
    assert result["us_pronunciation"] == "/ˈpriːloʊd/"


def test_lookup_word_keeps_placeholder_when_llm_also_fails(monkeypatch):
    entries = [
        {
            "phonetics": [{"audio": "https://.../preload-au.mp3"}],
            "meanings": [
                {
                    "partOfSpeech": "verb",
                    "definitions": [{"definition": "to load in advance"}],
                }
            ],
        }
    ]
    monkeypatch.setattr(
        dictionary.requests, "get", lambda *a, **kw: _FakeResponse(200, entries)
    )
    monkeypatch.setattr(dictionary, "translate_to_chinese", lambda text: "预先装入")
    monkeypatch.setattr(dictionary, "request_ipa_pronunciation", lambda word: None)

    result = dictionary.lookup_word("preload")
    assert result["en_pronunciation"] == "-"
    assert result["us_pronunciation"] == "-"


def test_lookup_word_llm_missing_api_key_falls_back_to_placeholder(monkeypatch):
    entries = [
        {
            "phonetics": [{"audio": "https://.../preload-au.mp3"}],
            "meanings": [
                {
                    "partOfSpeech": "verb",
                    "definitions": [{"definition": "to load in advance"}],
                }
            ],
        }
    ]
    monkeypatch.setattr(
        dictionary.requests, "get", lambda *a, **kw: _FakeResponse(200, entries)
    )
    monkeypatch.setattr(dictionary, "translate_to_chinese", lambda text: "预先装入")

    def boom(word):
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")

    monkeypatch.setattr(dictionary, "request_ipa_pronunciation", boom)

    result = dictionary.lookup_word("preload")
    assert result["en_pronunciation"] == "-"
    assert result["us_pronunciation"] == "-"
