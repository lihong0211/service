# service/en_desktop/roots.py
"""
en-desktop 词根服务：CRUD + 列表 + 关联例词（root_words 关联 words 表）
"""
from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import EnDesktopRoot, EnDesktopRootWord, EnDesktopWord


def _words_by_root(root_ids: list) -> dict:
    """root_id -> [{id, word}]，一次查询代替逐词根查询"""
    grouped = {}
    if not root_ids:
        return grouped
    rows = (
        db.session.query(EnDesktopRootWord, EnDesktopWord)
        .join(EnDesktopWord, EnDesktopWord.id == EnDesktopRootWord.word_id)
        .where(
            EnDesktopRootWord.root_id.in_(root_ids),
            EnDesktopRootWord.deleted_at.is_(None),
            EnDesktopWord.deleted_at.is_(None),
        )
        .order_by(EnDesktopRootWord.id.asc())
        .all()
    )
    for link, word in rows:
        grouped.setdefault(link.root_id, []).append({"id": word.id, "word": word.word})
    return grouped


def _pack(data: dict) -> dict:
    similar = data.get("similar")
    return {
        "name": data.get("name"),
        "meaning": data.get("meaning"),
        "similar": ",".join(similar) if isinstance(similar, list) else similar,
    }


def list_roots() -> dict:
    try:
        rows = EnDesktopRoot.select_by()
        words_by_root = _words_by_root([r.id for r in rows])
        return {
            "code": 200,
            "msg": "success",
            "data": [r.to_dict(words=words_by_root.get(r.id, [])) for r in rows],
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_root(data: dict) -> dict:
    if not (data.get("name") or "").strip():
        return {"code": 400, "msg": "name 不能为空"}
    try:
        root_id = EnDesktopRoot.insert(_pack(data))
        return {"code": 200, "msg": "success", "data": EnDesktopRoot.get_by_id(root_id).to_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update_root(root_id: int, data: dict) -> dict:
    try:
        existing = EnDesktopRoot.get_by_id(root_id)
        if not existing:
            return {"code": 500, "msg": "词根不存在"}
        EnDesktopRoot.update({"id": root_id, **_pack(data)})
        return {"code": 200, "msg": "success", "data": EnDesktopRoot.get_by_id(root_id).to_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete_root(root_id: int) -> dict:
    try:
        EnDesktopRoot.delete(root_id)
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_word(root_id: int, word_id: int) -> dict:
    try:
        if not EnDesktopRoot.get_by_id(root_id):
            return {"code": 400, "msg": "词根不存在"}
        if not EnDesktopWord.get_by_id(word_id):
            return {"code": 400, "msg": "单词不存在"}
        existing = (
            db.session.query(EnDesktopRootWord)
            .where(EnDesktopRootWord.root_id == root_id, EnDesktopRootWord.word_id == word_id)
            .first()
        )
        if existing and existing.deleted_at is None:
            return {"code": 400, "msg": "该例词已关联"}
        if existing:
            db.session.query(EnDesktopRootWord).where(EnDesktopRootWord.id == existing.id).update(
                {"deleted_at": None}
            )
        else:
            EnDesktopRootWord.insert({"root_id": root_id, "word_id": word_id}, commit=False)
        db.session.commit()
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def remove_word(root_id: int, word_id: int) -> dict:
    try:
        EnDesktopRootWord.delete_by({"root_id": root_id, "word_id": word_id})
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)
