"""
en-desktop 单词服务测试
"""
import pytest

from model.en_desktop import EnDesktopUser, EnDesktopWord, EnDesktopWordMeaning, EnDesktopWordSentence
from service.en_desktop import words

WORD_PAYLOAD = {
    "word": "apple",
    "en_pronunciation": "/ˈæp.əl/",
    "us_pronunciation": "/ˈæp.əl/",
    "meaning": [{"type": "n.", "content": "苹果"}],
}


@pytest.fixture
def user_id(en_desktop_db):
    return EnDesktopUser.insert({"username": "alice"})


def test_add_and_get_word(en_desktop_db):
    result = words.add_word(dict(WORD_PAYLOAD))
    assert result["code"] == 200
    word_id = result["data"]["id"]
    assert result["data"]["meaning"] == [
        {"type": "n.", "content": "苹果", "sentence": None}
    ]

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
    assert len(page1["data"]["list"]) == 10
    assert page1["data"]["total"] == 15
    assert len(page2["data"]["list"]) == 5
    assert page1["data"]["list"][0]["meaning"]


def test_list_words_marks_favorited_for_current_user(user_id):
    word_id = words.add_word(dict(WORD_PAYLOAD))["data"]["id"]

    # 未登录：favorited 恒为 False
    anon = words.list_words(page=1, page_size=10)
    assert anon["data"]["list"][0]["favorited"] is False

    # 登录但还没收藏：也是 False
    result = words.list_words(page=1, page_size=10, user_id=user_id)
    assert result["data"]["list"][0]["favorited"] is False

    # 收进"默认收藏"后：True，且只对这个用户成立
    words.add_word({**WORD_PAYLOAD, "library_id": "default"}, user_id=user_id)
    result = words.list_words(page=1, page_size=10, user_id=user_id)
    assert result["data"]["list"][0]["favorited"] is True
    assert result["data"]["list"][0]["id"] == word_id


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


def test_lookup_marks_saved(user_id, monkeypatch):
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

    # 词进了全局词典表，但还没收进任何人的"默认收藏"：saved 不该因此变 True
    words.add_word(dict(WORD_PAYLOAD))
    result = words.lookup({"word": "apple"}, user_id)
    assert result["data"]["saved"] is False

    # 未登录查词：即使这个词已经被 user_id 收藏了，也无法得知，恒为 False
    words.add_word({**WORD_PAYLOAD, "library_id": "default"}, user_id=user_id)
    assert words.lookup({"word": "apple"})["data"]["saved"] is False

    # 登录后查同一个词：确实在自己的"默认收藏"里，saved 才是 True
    result = words.lookup({"word": "apple"}, user_id)
    assert result["data"]["saved"] is True


def test_lookup_marks_saved_vocab_independently_of_default(user_id, monkeypatch):
    """saved（默认收藏）和 saved_vocab（生词本）是两个独立的收藏目标，互不影响"""
    fake = {
        "word": "apple",
        "meaning": [{"type": "n.", "content": "苹果"}],
        "en_pronunciation": "/ˈæp.əl/",
        "us_pronunciation": "/ˈæp.əl/",
    }
    monkeypatch.setattr(words.dictionary, "lookup_word", lambda w: dict(fake))

    words.add_word({**WORD_PAYLOAD, "library_id": "default"}, user_id=user_id)
    result = words.lookup({"word": "apple"}, user_id)
    assert result["data"]["saved"] is True
    assert result["data"]["saved_vocab"] is False

    words.add_word({**WORD_PAYLOAD, "library_id": "review"}, user_id=user_id)
    result = words.lookup({"word": "apple"}, user_id)
    assert result["data"]["saved"] is True
    assert result["data"]["saved_vocab"] is True


def test_add_word_with_review_library_sentinel(user_id):
    result = words.add_word({**WORD_PAYLOAD, "library_id": "review"}, user_id=user_id)
    assert result["code"] == 200

    from service.en_desktop import libraries as libraries_service

    review_lib = libraries_service.ensure_review_library(user_id)
    lib_words = libraries_service.library_words(user_id, review_lib.id)
    assert lib_words["data"]["total"] == 1
    assert lib_words["data"]["list"][0]["word"] == "apple"


def test_remove_from_library_toggles_saved_state(user_id, monkeypatch):
    """划词弹窗的取消收藏：加入后能再移除，而不是加入了就锁死"""
    fake = {
        "word": "apple",
        "meaning": [{"type": "n.", "content": "苹果"}],
        "en_pronunciation": "/ˈæp.əl/",
        "us_pronunciation": "/ˈæp.əl/",
    }
    monkeypatch.setattr(words.dictionary, "lookup_word", lambda w: dict(fake))

    words.add_word({**WORD_PAYLOAD, "library_id": "default"}, user_id=user_id)
    assert words.lookup({"word": "apple"}, user_id)["data"]["saved"] is True

    result = words.remove_from_library({"word": "apple", "library_id": "default"}, user_id)
    assert result["code"] == 200
    assert words.lookup({"word": "apple"}, user_id)["data"]["saved"] is False

    # 移除后还能再加回去（不是一次性操作）
    words.add_word({**WORD_PAYLOAD, "library_id": "default"}, user_id=user_id)
    assert words.lookup({"word": "apple"}, user_id)["data"]["saved"] is True


def test_remove_from_library_validation_and_idempotency(user_id):
    words.add_word(dict(WORD_PAYLOAD))
    assert words.remove_from_library({"word": "", "library_id": "default"}, user_id)["code"] == 400
    assert words.remove_from_library({"word": "apple", "library_id": ""}, user_id)["code"] == 400
    assert words.remove_from_library({"word": "apple", "library_id": "default"}, None)["code"] == 401
    assert words.remove_from_library({"word": "apple", "library_id": "bogus"}, user_id)["code"] == 400
    # 单词压根不存在：幂等地当成功处理，不报错
    assert words.remove_from_library({"word": "nonexistent", "library_id": "default"}, user_id)["code"] == 200


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


def test_get_word_meaning_carries_sentence(en_desktop_db):
    word_id = words.add_word(dict(WORD_PAYLOAD))["data"]["id"]
    meaning = EnDesktopWordMeaning.select_by({"word_id": word_id})[0]
    EnDesktopWordSentence.insert(
        {
            "word_meaning_id": meaning.id,
            "en_text": "I ate an apple.",
            "zh_text": "我吃了一个苹果。",
            "audio_url": None,
        }
    )

    result = words.get_word(word_id)
    assert result["data"]["meaning"][0]["sentence"] == {
        "en_text": "I ate an apple.",
        "zh_text": "我吃了一个苹果。",
        "audio_url": None,
    }
