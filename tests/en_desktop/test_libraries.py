"""
en-desktop 词库服务测试
"""
import pytest

from model.en_desktop import (
    EnDesktopUser,
    EnDesktopWordLibrary,
    EnDesktopWordLibraryItem,
    EnDesktopWordMeaning,
    EnDesktopWordSentence,
)
from service.en_desktop import libraries, words
from service.en_desktop.libraries import DEFAULT_LIBRARY_NAME


@pytest.fixture
def user_id(en_desktop_db):
    return EnDesktopUser.insert({"username": "alice"})


@pytest.fixture
def other_user_id(en_desktop_db):
    return EnDesktopUser.insert({"username": "bob"})


def _add_word(word_text="apple"):
    return words.add_word(
        {
            "word": word_text,
            "en_pronunciation": "/x/",
            "us_pronunciation": "/x/",
            "meaning": [{"type": "n.", "content": "释义"}],
        }
    )["data"]["id"]


def test_list_auto_creates_default_libraries(user_id):
    result = libraries.list_libraries(user_id)
    assert result["code"] == 200
    # list_libraries 不保证顺序（数据库物理返回顺序，加了唯一索引后也可能变），只比较集合
    names = {l["name"] for l in result["data"]}
    assert names == {DEFAULT_LIBRARY_NAME, libraries.REVIEW_LIBRARY_NAME}
    assert all(l["word_count"] == 0 for l in result["data"])

    # 再次 list 不会重复创建
    assert len(libraries.list_libraries(user_id)["data"]) == 2


def test_add_rename_delete_library(user_id):
    lib = libraries.add_library(user_id, {"name": "四级词汇"})
    assert lib["code"] == 200
    lib_id = lib["data"]["id"]

    assert libraries.add_library(user_id, {"name": "四级词汇"})["code"] == 400
    assert libraries.add_library(user_id, {"name": ""})["code"] == 400

    renamed = libraries.update_library(user_id, lib_id, {"name": "六级词汇"})
    assert renamed["code"] == 200
    assert renamed["data"]["name"] == "六级词汇"

    assert libraries.delete_library(user_id, lib_id)["code"] == 200


def test_add_library_concurrent_duplicate_hits_db_constraint(user_id):
    """
    并发建同名词库的回归测试：前端一次误触发（keyup.enter 级联出 blur）
    会发出两个几乎同时的建库请求，应用层"先查是否存在再插入"的检查不是原子
    操作，两个请求都可能通过检查。直接绕过 add_library 的检查、在它背后插入
    一条同名记录来模拟这个竞态，验证唯一约束 + IntegrityError 处理能正确
    兜底成友好提示，而不是让请求 500。
    """
    EnDesktopWordLibrary.insert({"user_id": user_id, "name": "并发词库"})
    result = libraries.add_library(user_id, {"name": "并发词库"})
    assert result["code"] == 400
    assert result["msg"] == "同名词库已存在"
    names = [l["name"] for l in libraries.list_libraries(user_id)["data"]]
    assert "六级词汇" not in names


def test_default_libraries_protected(user_id):
    for lib in libraries.list_libraries(user_id)["data"]:
        assert libraries.update_library(user_id, lib["id"], {"name": "x"})["code"] == 400
        assert libraries.delete_library(user_id, lib["id"])["code"] == 400


def test_library_ownership_isolation(user_id, other_user_id):
    lib_id = libraries.add_library(user_id, {"name": "私有词库"})["data"]["id"]

    assert libraries.update_library(other_user_id, lib_id, {"name": "偷改"})["code"] == 400
    assert libraries.delete_library(other_user_id, lib_id)["code"] == 400
    assert libraries.library_words(other_user_id, lib_id)["code"] == 400
    word_id = _add_word()
    result = libraries.add_word_to_library(
        other_user_id, {"library_id": lib_id, "word_id": word_id}
    )
    assert result["code"] == 400


def test_add_remove_readd_word(user_id):
    lib_id = libraries.add_library(user_id, {"name": "测试库"})["data"]["id"]
    word_id = _add_word()

    assert (
        libraries.add_word_to_library(user_id, {"library_id": lib_id, "word_id": word_id})["code"]
        == 200
    )
    # 重复添加报已存在
    assert (
        libraries.add_word_to_library(user_id, {"library_id": lib_id, "word_id": word_id})["code"]
        == 400
    )

    listed = libraries.library_words(user_id, lib_id)
    assert [w["word"] for w in listed["data"]["list"]] == ["apple"]

    # 移出后再加回（软删恢复，不撞唯一键）
    assert (
        libraries.remove_word_from_library(user_id, {"library_id": lib_id, "word_id": word_id})[
            "code"
        ]
        == 200
    )
    assert libraries.library_words(user_id, lib_id)["data"]["list"] == []
    assert (
        libraries.add_word_to_library(user_id, {"library_id": lib_id, "word_id": word_id})["code"]
        == 200
    )
    assert len(libraries.library_words(user_id, lib_id)["data"]["list"]) == 1

    counts = {l["id"]: l["word_count"] for l in libraries.list_libraries(user_id)["data"]}
    assert counts[lib_id] == 1


def test_add_word_with_default_library(user_id):
    """/words/add 带 library_id="default"：单词入库并进默认收藏"""
    result = words.add_word(
        {
            "word": "banana",
            "en_pronunciation": "/x/",
            "us_pronunciation": "/x/",
            "meaning": [{"type": "n.", "content": "香蕉"}],
            "library_id": "default",
        },
        user_id=user_id,
    )
    assert result["code"] == 200

    default = next(
        l
        for l in libraries.list_libraries(user_id)["data"]
        if l["name"] == DEFAULT_LIBRARY_NAME
    )
    assert default["word_count"] == 1

    # 已存在的单词再收藏：幂等成功，不报"单词已存在"
    again = words.add_word(
        {
            "word": "banana",
            "en_pronunciation": "/x/",
            "us_pronunciation": "/x/",
            "library_id": "default",
        },
        user_id=user_id,
    )
    assert again["code"] == 200
    assert (
        next(
            l
            for l in libraries.list_libraries(user_id)["data"]
            if l["name"] == DEFAULT_LIBRARY_NAME
        )["word_count"]
        == 1
    )


def test_add_word_library_requires_auth(en_desktop_db):
    result = words.add_word(
        {
            "word": "cherry",
            "en_pronunciation": "/x/",
            "us_pronunciation": "/x/",
            "library_id": "default",
        }
    )
    assert result["code"] == 401


def test_public_library_visible_and_readable_by_others(user_id, other_user_id):
    """公共词库：出现在 public 列表，任何用户可读词，但非属主不可改/删"""
    from model.en_desktop import EnDesktopWordLibrary

    lib_id = libraries.add_library(user_id, {"name": "系统四级"})["data"]["id"]
    EnDesktopWordLibrary.update({"id": lib_id, "is_public": 1})
    word_id = _add_word()
    libraries.add_word_to_library(user_id, {"library_id": lib_id, "word_id": word_id})

    public = libraries.list_public_libraries(other_user_id)
    assert public["code"] == 200
    entry = next(l for l in public["data"] if l["id"] == lib_id)
    assert entry["word_count"] == 1
    assert entry["favorited"] is False

    # 其他用户可读公共词库的单词
    listed = libraries.library_words(other_user_id, lib_id)
    assert listed["code"] == 200
    assert [w["word"] for w in listed["data"]["list"]] == ["apple"]

    # 但不能改/删/往里加词
    assert libraries.update_library(other_user_id, lib_id, {"name": "x"})["code"] == 400
    assert libraries.delete_library(other_user_id, lib_id)["code"] == 400
    assert (
        libraries.add_word_to_library(other_user_id, {"library_id": lib_id, "word_id": word_id})[
            "code"
        ]
        == 400
    )


def test_private_library_not_in_public_list_nor_readable(user_id, other_user_id):
    lib_id = libraries.add_library(user_id, {"name": "私有库"})["data"]["id"]
    assert all(l["id"] != lib_id for l in libraries.list_public_libraries(user_id)["data"])
    assert libraries.library_words(other_user_id, lib_id)["code"] == 400


def test_favorite_unfavorite_refavorite(user_id, other_user_id):
    from model.en_desktop import EnDesktopWordLibrary

    lib_id = libraries.add_library(user_id, {"name": "系统主题库"})["data"]["id"]
    EnDesktopWordLibrary.update({"id": lib_id, "is_public": 1})

    # 收藏 → favorites 列表出现，public 列表 favorited=True
    assert libraries.favorite_library(other_user_id, lib_id)["code"] == 200
    favs = libraries.list_favorites(other_user_id)
    assert [l["id"] for l in favs["data"]] == [lib_id]
    entry = next(l for l in libraries.list_public_libraries(other_user_id)["data"] if l["id"] == lib_id)
    assert entry["favorited"] is True

    # 重复收藏幂等
    assert libraries.favorite_library(other_user_id, lib_id)["code"] == 200
    assert len(libraries.list_favorites(other_user_id)["data"]) == 1

    # 取消 → 再收藏（软删恢复，不撞唯一键）
    assert libraries.unfavorite_library(other_user_id, lib_id)["code"] == 200
    assert libraries.list_favorites(other_user_id)["data"] == []
    assert libraries.favorite_library(other_user_id, lib_id)["code"] == 200
    assert len(libraries.list_favorites(other_user_id)["data"]) == 1


def test_favorite_private_library_rejected(user_id, other_user_id):
    lib_id = libraries.add_library(user_id, {"name": "私有不可收藏"})["data"]["id"]
    assert libraries.favorite_library(other_user_id, lib_id)["code"] == 400
    assert libraries.favorite_library(other_user_id, None)["code"] == 400


def test_delete_library_removes_items(user_id):
    lib_id = libraries.add_library(user_id, {"name": "临时库"})["data"]["id"]
    word_id = _add_word()
    libraries.add_word_to_library(user_id, {"library_id": lib_id, "word_id": word_id})

    libraries.delete_library(user_id, lib_id)
    active_items = EnDesktopWordLibraryItem.select_by({"word_library_id": lib_id})
    assert active_items == []


def test_library_words_meaning_carries_sentence(user_id):
    word_id = _add_word("apple")
    lib_id = libraries.list_libraries(user_id)["data"][0]["id"]
    libraries.add_item(lib_id, word_id)

    meaning = EnDesktopWordMeaning.select_by({"word_id": word_id})[0]
    EnDesktopWordSentence.insert(
        {
            "word_meaning_id": meaning.id,
            "en_text": "I ate an apple.",
            "zh_text": "我吃了一个苹果。",
            "audio_url": "https://doctor-dog.com/static/word_sentences/1.mp3",
        }
    )

    result = libraries.library_words(user_id, lib_id)
    word = result["data"]["list"][0]
    assert word["meaning"][0]["sentence"] == {
        "en_text": "I ate an apple.",
        "zh_text": "我吃了一个苹果。",
        "audio_url": "https://doctor-dog.com/static/word_sentences/1.mp3",
    }


def test_library_words_meaning_without_sentence_is_none(user_id):
    word_id = _add_word("banana")
    lib_id = libraries.list_libraries(user_id)["data"][0]["id"]
    libraries.add_item(lib_id, word_id)

    result = libraries.library_words(user_id, lib_id)
    word = result["data"]["list"][0]
    assert word["meaning"][0]["sentence"] is None


def test_library_words_favorited_flag_reflects_default_library(user_id):
    word_id = _add_word("cherry")
    default_lib = next(
        lib
        for lib in libraries.list_libraries(user_id)["data"]
        if lib["name"] == DEFAULT_LIBRARY_NAME
    )
    other_lib_id = libraries.add_library(user_id, {"name": "水果"})["data"]["id"]
    libraries.add_item(other_lib_id, word_id)

    result = libraries.library_words(user_id, other_lib_id)
    assert result["data"]["list"][0]["favorited"] is False

    libraries.add_item(default_lib["id"], word_id)
    result = libraries.library_words(user_id, other_lib_id)
    assert result["data"]["list"][0]["favorited"] is True


def test_library_words_favorited_flag_false_when_unauthenticated(user_id):
    word_id = _add_word("date")
    pub_lib_id = libraries.add_library(
        user_id, {"name": "公共词库", "is_public": True}
    )["data"]["id"]
    libraries.add_item(pub_lib_id, word_id)

    result = libraries.library_words(None, pub_lib_id)
    assert result["data"]["list"][0]["favorited"] is False
