# service/en_desktop/libraries.py
"""
en-desktop 词库服务（歌单式）：词库 CRUD + 词库内单词管理。
所有操作按 user_id 隔离；"默认收藏"是每个用户的默认词库，自动创建、不可改名/删除。
"""
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import (
    EnDesktopWord,
    EnDesktopWordLibrary,
    EnDesktopWordLibraryFavorite,
    EnDesktopWordLibraryItem,
    EnDesktopWordMeaning,
    EnDesktopWordSentence,
)

DEFAULT_LIBRARY_NAME = "默认收藏"
REVIEW_LIBRARY_NAME = "未掌握"
# 系统默认词库（自动创建、不可改名/删除）：默认收藏=划词收藏入口，未掌握=复习清单
PROTECTED_LIBRARY_NAMES = (DEFAULT_LIBRARY_NAME, REVIEW_LIBRARY_NAME)


def _ensure_named_library(user_id: int, name: str) -> EnDesktopWordLibrary:
    lib = EnDesktopWordLibrary.select_one_by({"user_id": user_id, "name": name})
    if lib:
        return lib
    lib_id = EnDesktopWordLibrary.insert({"user_id": user_id, "name": name})
    return EnDesktopWordLibrary.get_by_id(lib_id)


def ensure_default_library(user_id: int) -> EnDesktopWordLibrary:
    """划词收藏的默认词库，不存在则创建"""
    return _ensure_named_library(user_id, DEFAULT_LIBRARY_NAME)


def ensure_review_library(user_id: int) -> EnDesktopWordLibrary:
    """未掌握（复习）词库，不存在则创建"""
    return _ensure_named_library(user_id, REVIEW_LIBRARY_NAME)


def owned_library(user_id: int, library_id: int) -> EnDesktopWordLibrary | None:
    lib = EnDesktopWordLibrary.get_by_id(library_id)
    if not lib or lib.user_id != user_id:
        return None
    return lib


def _sentences_grouped(meaning_ids: list) -> dict:
    """word_meaning_id -> {en_text, zh_text, audio_url}，一次查询代替逐条查询"""
    grouped = {}
    if not meaning_ids:
        return grouped
    rows = (
        db.session.query(EnDesktopWordSentence)
        .where(
            EnDesktopWordSentence.word_meaning_id.in_(meaning_ids),
            EnDesktopWordSentence.deleted_at.is_(None),
        )
        .all()
    )
    for s in rows:
        grouped[s.word_meaning_id] = {
            "en_text": s.en_text,
            "zh_text": s.zh_text,
            "audio_url": s.audio_url,
        }
    return grouped


def _meanings_grouped(word_ids: list) -> dict:
    """word_id -> [{type, content, sentence}]，一次查询代替逐词查询"""
    grouped = {}
    if not word_ids:
        return grouped
    rows = (
        db.session.query(EnDesktopWordMeaning)
        .where(
            EnDesktopWordMeaning.word_id.in_(word_ids),
            EnDesktopWordMeaning.deleted_at.is_(None),
        )
        .order_by(EnDesktopWordMeaning.id.asc())
        .all()
    )
    sentences = _sentences_grouped([m.id for m in rows])
    for m in rows:
        grouped.setdefault(m.word_id, []).append(
            {"type": m.type, "content": m.content, "sentence": sentences.get(m.id)}
        )
    return grouped


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
        ensure_review_library(user_id)
        libs = EnDesktopWordLibrary.select_by({"user_id": user_id})
        return {
            "code": 200,
            "msg": "success",
            "data": [lib.to_dict(word_count=_word_count(lib.id)) for lib in libs],
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def _favorited_ids(user_id: int) -> set:
    favs = EnDesktopWordLibraryFavorite.select_by({"user_id": user_id})
    return {f.word_library_id for f in favs}


def list_public_libraries(user_id: int | None) -> dict:
    """公共（系统）词库列表，不登录也可浏览；favorited 标记当前用户是否已收藏（未登录恒为 False）"""
    try:
        favorited = _favorited_ids(user_id) if user_id else set()
        libs = EnDesktopWordLibrary.select_by({"is_public": 1})
        return {
            "code": 200,
            "msg": "success",
            "data": [
                {**lib.to_dict(word_count=_word_count(lib.id)), "favorited": lib.id in favorited}
                for lib in libs
            ],
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def list_favorites(user_id: int) -> dict:
    """当前用户收藏的公共词库"""
    try:
        favorited = _favorited_ids(user_id)
        if not favorited:
            return {"code": 200, "msg": "success", "data": []}
        libs = (
            db.session.query(EnDesktopWordLibrary)
            .where(
                EnDesktopWordLibrary.id.in_(favorited),
                EnDesktopWordLibrary.deleted_at.is_(None),
            )
            .all()
        )
        return {
            "code": 200,
            "msg": "success",
            "data": [
                {**lib.to_dict(word_count=_word_count(lib.id)), "favorited": True}
                for lib in libs
            ],
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def favorite_library(user_id: int, library_id: int) -> dict:
    """收藏公共词库；曾取消过的恢复原纪录（绕开唯一键冲突）"""
    try:
        lib = EnDesktopWordLibrary.get_by_id(library_id)
        if not lib or not lib.is_public:
            return {"code": 400, "msg": "词库不存在或不可收藏"}

        existing = (
            db.session.query(EnDesktopWordLibraryFavorite)
            .where(
                EnDesktopWordLibraryFavorite.user_id == user_id,
                EnDesktopWordLibraryFavorite.word_library_id == library_id,
            )
            .first()
        )
        if existing and existing.deleted_at is None:
            return {"code": 200, "msg": "success", "data": None}
        if existing:
            existing.deleted_at = None
        else:
            db.session.add(
                EnDesktopWordLibraryFavorite(user_id=user_id, word_library_id=library_id)
            )
        db.session.commit()
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def unfavorite_library(user_id: int, library_id: int) -> dict:
    try:
        EnDesktopWordLibraryFavorite.delete_by(
            {"user_id": user_id, "word_library_id": library_id}
        )
        return {"code": 200, "msg": "success", "data": None}
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
            {
                "user_id": user_id,
                "name": name,
                "description": data.get("description"),
                "is_public": 1 if data.get("is_public") else 0,
            }
        )
        return {
            "code": 200,
            "msg": "success",
            "data": EnDesktopWordLibrary.get_by_id(lib_id).to_dict(),
        }
    except IntegrityError:
        # 上面的存在性检查不是原子操作：两个并发请求都可能先后通过检查再各自插入，
        # 靠 (user_id, name) 唯一约束在数据库层兜底，命中即为并发建同名库
        db.session.rollback()
        return {"code": 400, "msg": "同名词库已存在"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update_library(user_id: int, library_id: int, data: dict) -> dict:
    try:
        lib = owned_library(user_id, library_id)
        if not lib:
            return {"code": 400, "msg": "词库不存在"}
        if lib.name in PROTECTED_LIBRARY_NAMES:
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
        if data.get("is_public") is not None:
            update_dict["is_public"] = 1 if data["is_public"] else 0
        EnDesktopWordLibrary.update(update_dict)
        return {
            "code": 200,
            "msg": "success",
            "data": EnDesktopWordLibrary.get_by_id(library_id).to_dict(
                word_count=_word_count(library_id)
            ),
        }
    except IntegrityError:
        db.session.rollback()
        return {"code": 400, "msg": "同名词库已存在"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete_library(user_id: int, library_id: int) -> dict:
    try:
        lib = owned_library(user_id, library_id)
        if not lib:
            return {"code": 400, "msg": "词库不存在"}
        if lib.name in PROTECTED_LIBRARY_NAMES:
            return {"code": 400, "msg": "默认词库不能删除"}

        EnDesktopWordLibraryItem.delete_by({"word_library_id": library_id}, commit=False)
        EnDesktopWordLibrary.delete(library_id, commit=False)
        db.session.commit()
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def library_words(
    user_id: int | None,
    library_id: int,
    page: int = 1,
    page_size: int = 10,
    search: str | None = None,
) -> dict:
    """分页返回 {list, total, page, page_size}；search 按单词模糊匹配"""
    try:
        # 自己的词库可读，公共词库不登录也可读；改/删仍只限属主
        lib = EnDesktopWordLibrary.get_by_id(library_id)
        if not lib or (lib.user_id != user_id and not lib.is_public):
            return {"code": 400, "msg": "词库不存在"}

        query = (
            db.session.query(EnDesktopWordLibraryItem, EnDesktopWord)
            .join(EnDesktopWord, EnDesktopWord.id == EnDesktopWordLibraryItem.word_id)
            .where(
                EnDesktopWordLibraryItem.word_library_id == library_id,
                EnDesktopWordLibraryItem.deleted_at.is_(None),
                EnDesktopWord.deleted_at.is_(None),
            )
        )
        if search:
            query = query.where(EnDesktopWord.word.like(f"%{search.strip()}%"))
        total = query.count()
        rows = (
            query.order_by(EnDesktopWordLibraryItem.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        page_words = [word for _, word in rows]
        meanings_by_word = _meanings_grouped([w.id for w in page_words])
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "list": [
                    w.to_dict(meaning=meanings_by_word.get(w.id, [])) for w in page_words
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        }
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
