"""
en-desktop 单词服务测试
"""
from model.en_desktop import EnDesktopWord, EnDesktopWordMeaning
from service.en_desktop import words

WORD_PAYLOAD = {
    "word": "apple",
    "en_pronunciation": "/ˈæp.əl/",
    "us_pronunciation": "/ˈæp.əl/",
    "meaning": [{"type": "n.", "content": "苹果"}],
}


def test_add_and_get_word(en_desktop_db):
    result = words.add_word(dict(WORD_PAYLOAD))
    assert result["code"] == 200
    word_id = result["data"]["id"]
    assert result["data"]["meaning"] == [{"type": "n.", "content": "苹果"}]

    got = words.get_word(word_id)
    assert got["code"] == 200
    assert got["data"]["word"] == "apple"


def test_add_duplicate_word(en_desktop_db):
    words.add_word(dict(WORD_PAYLOAD))
    result = words.add_word(dict(WORD_PAYLOAD))
    assert result["code"] == 500
    assert result["msg"] == "单词已存在"


def test_add_word_validation(en_desktop_db):
    assert words.add_word({"word": ""})["code"] == 400
    assert words.add_word({"word": "x" * 31})["code"] == 400
    assert words.add_word({"word": "ok"})["code"] == 400  # 缺音标


def test_list_words_pagination(en_desktop_db):
    for i in range(15):
        words.add_word(
            {
                "word": f"word{i:02d}",
                "en_pronunciation": "/x/",
                "us_pronunciation": "/x/",
                "meaning": [{"type": "n.", "content": f"释义{i}"}],
            }
        )
    page1 = words.list_words(page=1, page_size=10)
    page2 = words.list_words(page=2, page_size=10)
    assert page1["code"] == 200
    assert len(page1["data"]) == 10
    assert len(page2["data"]) == 5
    assert page1["data"][0]["meaning"]


def test_update_word_replaces_meanings(en_desktop_db):
    word_id = words.add_word(dict(WORD_PAYLOAD))["data"]["id"]

    result = words.update_word(
        word_id,
        {
            "word": "apples",
            "meaning": [
                {"type": "n.", "content": "苹果（复数）"},
                {"type": "v.", "content": "某动词"},
            ],
        },
    )
    assert result["code"] == 200
    assert result["data"]["word"] == "apples"
    assert len(result["data"]["meaning"]) == 2

    # 旧释义被软删除，不会残留
    active = EnDesktopWordMeaning.select_by({"word_id": word_id})
    assert len(active) == 2


def test_update_word_conflict_and_missing(en_desktop_db):
    words.add_word(dict(WORD_PAYLOAD))
    other_id = words.add_word(
        {
            "word": "banana",
            "en_pronunciation": "/x/",
            "us_pronunciation": "/x/",
            "meaning": [],
        }
    )["data"]["id"]

    result = words.update_word(other_id, {"word": "apple"})
    assert result["code"] == 500
    assert result["msg"] == "单词已存在"

    assert words.update_word(9999, {"word": "x"})["code"] == 500


def test_delete_word_is_soft(en_desktop_db):
    word_id = words.add_word(dict(WORD_PAYLOAD))["data"]["id"]
    assert words.delete_word(word_id)["code"] == 200
    assert words.get_word(word_id)["code"] == 500
    assert EnDesktopWord.get_by_id(word_id) is None


def test_lookup_marks_saved(en_desktop_db, monkeypatch):
    fake = {
        "word": "apple",
        "meaning": [{"type": "n.", "content": "苹果"}],
        "en_pronunciation": "/ˈæp.əl/",
        "us_pronunciation": "/ˈæp.əl/",
    }
    monkeypatch.setattr(words.dictionary, "lookup_word", lambda w: dict(fake))

    result = words.lookup({"word": "apple"})
    assert result["code"] == 200
    assert result["data"]["saved"] is False

    words.add_word(dict(WORD_PAYLOAD))
    result = words.lookup({"word": "apple"})
    assert result["data"]["saved"] is True


def test_lookup_not_found_and_error(en_desktop_db, monkeypatch):
    monkeypatch.setattr(words.dictionary, "lookup_word", lambda w: None)
    assert words.lookup({"word": "zzzz"})["code"] == 500

    def boom(w):
        raise RuntimeError("未配置 YOUDAO_APP_KEY / YOUDAO_APP_SECRET")

    monkeypatch.setattr(words.dictionary, "lookup_word", boom)
    result = words.lookup({"word": "apple"})
    assert result["code"] == 500
    assert "YOUDAO" in result["msg"]

    assert words.lookup({})["code"] == 400
