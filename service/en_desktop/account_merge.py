# service/en_desktop/account_merge.py
"""
账号合并：把 source_user 名下的词库和收藏迁移到 target_user，服务于 auth.bind_account。
只挂起 ORM 对象修改，不提交事务——commit 由调用方统一做（bind_account 里还要处理
wx_mini 过户和 flush 顺序，两者必须在同一个事务里）。

全程直接修改已取出的 ORM 对象属性（不用 EnDesktopModel.update()，那个方法会跳过 None
值，也不适合按名称查重后再改这种场景），跟 libraries.py 的 favorite_library() 是同一种
写法。
"""
from datetime import datetime

from app.database import db
from model.en_desktop import (
    EnDesktopWordLibrary,
    EnDesktopWordLibraryFavorite,
    EnDesktopWordLibraryItem,
)
from service.en_desktop.libraries import PROTECTED_LIBRARY_NAMES


def _merge_library_items(source_lib_id: int, target_lib_id: int) -> None:
    """source 默认词库的单词并入 target 同名默认词库：target 已有的对应 item 直接软删
    source 那条，没有的把 word_library_id 过户过去。"""
    target_word_ids = {
        row[0]
        for row in db.session.query(EnDesktopWordLibraryItem.word_id)
        .where(
            EnDesktopWordLibraryItem.word_library_id == target_lib_id,
            EnDesktopWordLibraryItem.deleted_at.is_(None),
        )
        .all()
    }
    source_items = (
        db.session.query(EnDesktopWordLibraryItem)
        .where(
            EnDesktopWordLibraryItem.word_library_id == source_lib_id,
            EnDesktopWordLibraryItem.deleted_at.is_(None),
        )
        .all()
    )
    for item in source_items:
        if item.word_id in target_word_ids:
            item.deleted_at = datetime.now()
        else:
            item.word_library_id = target_lib_id
            target_word_ids.add(item.word_id)


def merge_libraries_and_favorites(source_user_id: int, target_user_id: int) -> None:
    source_libs = EnDesktopWordLibrary.select_by({"user_id": source_user_id})
    target_libs_by_name = {
        lib.name: lib for lib in EnDesktopWordLibrary.select_by({"user_id": target_user_id})
    }

    for lib in source_libs:
        conflict = target_libs_by_name.get(lib.name)
        if conflict and lib.name in PROTECTED_LIBRARY_NAMES:
            # 默认词库（生词本/复习本）两边都有：词条合并进 target 的那份，source 这份删掉
            _merge_library_items(lib.id, conflict.id)
            EnDesktopWordLibrary.delete(lib.id, commit=False)
        elif conflict:
            # 自建词库同名冲突：改名后再过户，避免撞 (user_id, name) 唯一约束
            lib.name = f"{lib.name}（微信）"
            lib.user_id = target_user_id
        else:
            lib.user_id = target_user_id

    target_favorite_lib_ids = {
        row[0]
        for row in db.session.query(EnDesktopWordLibraryFavorite.word_library_id)
        .where(EnDesktopWordLibraryFavorite.user_id == target_user_id)
        .all()
    }
    for fav in EnDesktopWordLibraryFavorite.select_by({"user_id": source_user_id}):
        if fav.word_library_id in target_favorite_lib_ids:
            fav.deleted_at = datetime.now()
        else:
            fav.user_id = target_user_id
