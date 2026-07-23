"""
account_merge 合并逻辑测试：默认词库合并去重、自建库同名改名过户、收藏去重。
"""
from app.database import db
from model.en_desktop import (
    EnDesktopWordLibrary,
    EnDesktopWordLibraryFavorite,
    EnDesktopWordLibraryItem,
)
from service.en_desktop import account_merge, libraries


def _make_word(word_text: str):
    from model.en_desktop import EnDesktopWord

    return EnDesktopWord.insert({"word": word_text})


def test_merge_default_library_dedupes_items(en_desktop_db):
    source_lib = libraries.ensure_default_library(1)
    target_lib = libraries.ensure_default_library(2)

    shared_word = _make_word("apple")
    source_only_word = _make_word("banana")
    EnDesktopWordLibraryItem.insert({"word_library_id": source_lib.id, "word_id": shared_word})
    EnDesktopWordLibraryItem.insert({"word_library_id": source_lib.id, "word_id": source_only_word})
    EnDesktopWordLibraryItem.insert({"word_library_id": target_lib.id, "word_id": shared_word})

    account_merge.merge_libraries_and_favorites(source_user_id=1, target_user_id=2)
    db.session.commit()

    remaining_target_items = EnDesktopWordLibraryItem.select_by({"word_library_id": target_lib.id})
    assert {i.word_id for i in remaining_target_items} == {shared_word, source_only_word}
    # source 的默认库被软删
    assert EnDesktopWordLibrary.get_by_id(source_lib.id) is None


def test_merge_renames_conflicting_custom_library(en_desktop_db):
    source_lib_id = EnDesktopWordLibrary.insert({"user_id": 1, "name": "我的词库"})
    EnDesktopWordLibrary.insert({"user_id": 2, "name": "我的词库"})

    account_merge.merge_libraries_and_favorites(source_user_id=1, target_user_id=2)
    db.session.commit()

    target_libs = EnDesktopWordLibrary.select_by({"user_id": 2})
    names = {lib.name for lib in target_libs}
    assert "我的词库" in names
    assert "我的词库（微信）" in names
    assert EnDesktopWordLibrary.get_by_id(source_lib_id).user_id == 2


def test_merge_transfers_non_conflicting_library(en_desktop_db):
    source_lib_id = EnDesktopWordLibrary.insert({"user_id": 1, "name": "自建库A"})

    account_merge.merge_libraries_and_favorites(source_user_id=1, target_user_id=2)
    db.session.commit()

    lib = EnDesktopWordLibrary.get_by_id(source_lib_id)
    assert lib.user_id == 2
    assert lib.name == "自建库A"


def test_merge_favorites_dedupes(en_desktop_db):
    public_lib_id = EnDesktopWordLibrary.insert({"user_id": 99, "name": "公共库", "is_public": 1})
    other_public_lib_id = EnDesktopWordLibrary.insert(
        {"user_id": 99, "name": "公共库2", "is_public": 1}
    )
    db.session.add(EnDesktopWordLibraryFavorite(user_id=1, word_library_id=public_lib_id))
    db.session.add(EnDesktopWordLibraryFavorite(user_id=2, word_library_id=public_lib_id))
    db.session.add(EnDesktopWordLibraryFavorite(user_id=1, word_library_id=other_public_lib_id))
    db.session.commit()

    account_merge.merge_libraries_and_favorites(source_user_id=1, target_user_id=2)
    db.session.commit()

    target_favorites = EnDesktopWordLibraryFavorite.select_by({"user_id": 2})
    assert {f.word_library_id for f in target_favorites} == {public_lib_id, other_public_lib_id}
    source_favorites = EnDesktopWordLibraryFavorite.select_by({"user_id": 1})
    assert source_favorites == []
