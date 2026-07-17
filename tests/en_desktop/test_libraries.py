"""
en-desktop 词库服务测试
"""
import pytest

from model.en_desktop import EnDesktopUser, EnDesktopWordLibraryItem
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


def test_list_auto_creates_default_library(user_id):
    result = libraries.list_libraries(user_id)
    assert result["code"] == 200
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == DEFAULT_LIBRARY_NAME
    assert result["data"][0]["word_count"] == 0

    # 再次 list 不会重复创建
    assert len(libraries.list_libraries(user_id)["data"]) == 1


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
    names = [l["name"] for l in libraries.list_libraries(user_id)["data"]]
    assert "六级词汇" not in names


def test_default_library_protected(user_id):
    default = libraries.list_libraries(user_id)["data"][0]
    assert libraries.update_library(user_id, default["id"], {"name": "x"})["code"] == 400
    assert libraries.delete_library(user_id, default["id"])["code"] == 400


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
    assert [w["word"] for w in listed["data"]] == ["apple"]

    # 移出后再加回（软删恢复，不撞唯一键）
    assert (
        libraries.remove_word_from_library(user_id, {"library_id": lib_id, "word_id": word_id})[
            "code"
        ]
        == 200
    )
    assert libraries.library_words(user_id, lib_id)["data"] == []
    assert (
        libraries.add_word_to_library(user_id, {"library_id": lib_id, "word_id": word_id})["code"]
        == 200
    )
    assert len(libraries.library_words(user_id, lib_id)["data"]) == 1

    counts = {l["id"]: l["word_count"] for l in libraries.list_libraries(user_id)["data"]}
    assert counts[lib_id] == 1


def test_add_word_with_default_library(user_id):
    """/words/add 带 library_id="default"：单词入库并进我的收藏"""
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


def test_delete_library_removes_items(user_id):
    lib_id = libraries.add_library(user_id, {"name": "临时库"})["data"]["id"]
    word_id = _add_word()
    libraries.add_word_to_library(user_id, {"library_id": lib_id, "word_id": word_id})

    libraries.delete_library(user_id, lib_id)
    active_items = EnDesktopWordLibraryItem.select_by({"word_library_id": lib_id})
    assert active_items == []
