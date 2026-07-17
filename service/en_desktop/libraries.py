# service/en_desktop/libraries.py
"""
en-desktop 词库服务（歌单式）：词库 CRUD + 词库内单词管理。
所有操作按 user_id 隔离；"我的收藏"是每个用户的默认词库，自动创建、不可改名/删除。
"""
from datetime import datetime

from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import (
    EnDesktopWord,
    EnDesktopWordLibrary,
    EnDesktopWordLibraryItem,
    EnDesktopWordMeaning,
)

DEFAULT_LIBRARY_NAME = "我的收藏"


def ensure_default_library(user_id: int) -> EnDesktopWordLibrary:
    """默认词库不存在则创建"""
    lib = EnDesktopWordLibrary.select_one_by(
        {"user_id": user_id, "name": DEFAULT_LIBRARY_NAME}
    )
    if lib:
        return lib
    lib_id = EnDesktopWordLibrary.insert({"user_id": user_id, "name": DEFAULT_LIBRARY_NAME})
    return EnDesktopWordLibrary.get_by_id(lib_id)


def owned_library(user_id: int, library_id: int) -> EnDesktopWordLibrary | None:
    lib = EnDesktopWordLibrary.get_by_id(library_id)
    if not lib or lib.user_id != user_id:
        return None
    return lib


def _word_count(library_id: int) -> int:
    return (
        db.session.query(EnDesktopWordLibraryItem)
        .where(
            EnDesktopWordLibraryItem.word_library_id == library_id,
            EnDesktopWordLibraryItem.deleted_at.is_(None),
        )
        .count()
    )


def list_libraries(user_id: int) -> dict:
    try:
        ensure_default_library(user_id)
        libs = EnDesktopWordLibrary.select_by({"user_id": user_id})
        return {
            "code": 200,
            "msg": "success",
            "data": [lib.to_dict(word_count=_word_count(lib.id)) for lib in libs],
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_library(user_id: int, data: dict) -> dict:
    name = (data.get("name") or "").strip()
    if not 1 <= len(name) <= 50:
        return {"code": 400, "msg": "词库名称长度需在1-50个字符"}

    try:
        if EnDesktopWordLibrary.select_one_by({"user_id": user_id, "name": name}):
            return {"code": 400, "msg": "同名词库已存在"}
        lib_id = EnDesktopWordLibrary.insert(
            {"user_id": user_id, "name": name, "description": data.get("description")}
        )
        return {
            "code": 200,
            "msg": "success",
            "data": EnDesktopWordLibrary.get_by_id(lib_id).to_dict(),
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update_library(user_id: int, library_id: int, data: dict) -> dict:
    try:
        lib = owned_library(user_id, library_id)
        if not lib:
            return {"code": 400, "msg": "词库不存在"}
        if lib.name == DEFAULT_LIBRARY_NAME:
            return {"code": 400, "msg": "默认词库不能修改"}

        new_name = (data.get("name") or "").strip() if data.get("name") is not None else None
        if new_name is not None:
            if not 1 <= len(new_name) <= 50:
                return {"code": 400, "msg": "词库名称长度需在1-50个字符"}
            dup = EnDesktopWordLibrary.select_one_by({"user_id": user_id, "name": new_name})
            if dup and dup.id != library_id:
                return {"code": 400, "msg": "同名词库已存在"}

        update_dict = {"id": library_id}
        if new_name is not None:
            update_dict["name"] = new_name
        if data.get("description") is not None:
            update_dict["description"] = data["description"]
        EnDesktopWordLibrary.update(update_dict)
        return {
            "code": 200,
            "msg": "success",
            "data": EnDesktopWordLibrary.get_by_id(library_id).to_dict(
                word_count=_word_count(library_id)
            ),
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete_library(user_id: int, library_id: int) -> dict:
    try:
        lib = owned_library(user_id, library_id)
        if not lib:
            return {"code": 400, "msg": "词库不存在"}
        if lib.name == DEFAULT_LIBRARY_NAME:
            return {"code": 400, "msg": "默认词库不能删除"}

        EnDesktopWordLibraryItem.delete_by({"word_library_id": library_id}, commit=False)
        EnDesktopWordLibrary.delete(library_id, commit=False)
        db.session.commit()
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def library_words(user_id: int, library_id: int, page: int = 1, page_size: int = 10) -> dict:
    try:
        lib = owned_library(user_id, library_id)
        if not lib:
            return {"code": 400, "msg": "词库不存在"}

        items = (
            db.session.query(EnDesktopWordLibraryItem)
            .where(
                EnDesktopWordLibraryItem.word_library_id == library_id,
                EnDesktopWordLibraryItem.deleted_at.is_(None),
            )
            .order_by(EnDesktopWordLibraryItem.id.asc())
            .all()
        )
        start = (page - 1) * page_size
        page_items = items[start : start + page_size]

        data = []
        for item in page_items:
            word = EnDesktopWord.get_by_id(item.word_id)
            if not word:
                continue
            meanings = EnDesktopWordMeaning.select_by({"word_id": word.id})
            data.append(
                word.to_dict(meaning=[{"type": m.type, "content": m.content} for m in meanings])
            )
        return {"code": 200, "msg": "success", "data": data}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_word_to_library(user_id: int, data: dict) -> dict:
    library_id = data.get("library_id")
    word_id = data.get("word_id")
    if not library_id or not word_id:
        return {"code": 400, "msg": "library_id / word_id 不能为空"}

    try:
        if not owned_library(user_id, library_id):
            return {"code": 400, "msg": "词库不存在"}
        if not EnDesktopWord.get_by_id(word_id):
            return {"code": 400, "msg": "单词不存在"}
        result = add_item(library_id, word_id)
        db.session.commit()
        return result
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_item(library_id: int, word_id: int) -> dict:
    """加词到词库（不提交事务）。曾移出过的恢复原记录，绕开唯一键冲突。"""
    existing = (
        db.session.query(EnDesktopWordLibraryItem)
        .where(
            EnDesktopWordLibraryItem.word_library_id == library_id,
            EnDesktopWordLibraryItem.word_id == word_id,
        )
        .first()
    )
    if existing and existing.deleted_at is None:
        return {"code": 400, "msg": "单词已在词库中"}
    if existing:
        db.session.query(EnDesktopWordLibraryItem).where(
            EnDesktopWordLibraryItem.id == existing.id
        ).update({"deleted_at": None, "created_at": datetime.now()})
    else:
        EnDesktopWordLibraryItem.insert(
            {"word_library_id": library_id, "word_id": word_id}, commit=False
        )
    return {"code": 200, "msg": "success", "data": None}


def remove_word_from_library(user_id: int, data: dict) -> dict:
    library_id = data.get("library_id")
    word_id = data.get("word_id")
    if not library_id or not word_id:
        return {"code": 400, "msg": "library_id / word_id 不能为空"}

    try:
        if not owned_library(user_id, library_id):
            return {"code": 400, "msg": "词库不存在"}
        EnDesktopWordLibraryItem.delete_by(
            {"word_library_id": library_id, "word_id": word_id}
        )
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)
