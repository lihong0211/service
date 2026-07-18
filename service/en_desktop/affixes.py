# service/en_desktop/affixes.py
"""
en-desktop 词缀服务：CRUD + 列表 + 关联例词（affix_words 关联 words 表）
"""
from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import EnDesktopAffix, EnDesktopAffixWord, EnDesktopWord


def _words_by_affix(affix_ids: list) -> dict:
    """affix_id -> [{id, word}]，一次查询代替逐词缀查询"""
    grouped = {}
    if not affix_ids:
        return grouped
    rows = (
        db.session.query(EnDesktopAffixWord, EnDesktopWord)
        .join(EnDesktopWord, EnDesktopWord.id == EnDesktopAffixWord.word_id)
        .where(
            EnDesktopAffixWord.affix_id.in_(affix_ids),
            EnDesktopAffixWord.deleted_at.is_(None),
            EnDesktopWord.deleted_at.is_(None),
        )
        .order_by(EnDesktopAffixWord.id.asc())
        .all()
    )
    for link, word in rows:
        grouped.setdefault(link.affix_id, []).append({"id": word.id, "word": word.word})
    return grouped


def _pack(data: dict) -> dict:
    similar = data.get("similar")
    return {
        "name": data.get("name"),
        "meaning": data.get("meaning"),
        "similar": ",".join(similar) if isinstance(similar, list) else similar,
    }


def list_affixes() -> dict:
    try:
        rows = EnDesktopAffix.select_by()
        words_by_affix = _words_by_affix([r.id for r in rows])
        return {
            "code": 200,
            "msg": "success",
            "data": [r.to_dict(words=words_by_affix.get(r.id, [])) for r in rows],
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_affix(data: dict) -> dict:
    if not (data.get("name") or "").strip():
        return {"code": 400, "msg": "name 不能为空"}
    try:
        affix_id = EnDesktopAffix.insert(_pack(data))
        return {"code": 200, "msg": "success", "data": EnDesktopAffix.get_by_id(affix_id).to_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update_affix(affix_id: int, data: dict) -> dict:
    try:
        existing = EnDesktopAffix.get_by_id(affix_id)
        if not existing:
            return {"code": 500, "msg": "词缀不存在"}
        EnDesktopAffix.update({"id": affix_id, **_pack(data)})
        return {"code": 200, "msg": "success", "data": EnDesktopAffix.get_by_id(affix_id).to_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete_affix(affix_id: int) -> dict:
    try:
        EnDesktopAffix.delete(affix_id)
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_word(affix_id: int, word_id: int) -> dict:
    try:
        if not EnDesktopAffix.get_by_id(affix_id):
            return {"code": 400, "msg": "词缀不存在"}
        if not EnDesktopWord.get_by_id(word_id):
            return {"code": 400, "msg": "单词不存在"}
        existing = (
            db.session.query(EnDesktopAffixWord)
            .where(EnDesktopAffixWord.affix_id == affix_id, EnDesktopAffixWord.word_id == word_id)
            .first()
        )
        if existing and existing.deleted_at is None:
            return {"code": 400, "msg": "该例词已关联"}
        if existing:
            db.session.query(EnDesktopAffixWord).where(EnDesktopAffixWord.id == existing.id).update(
                {"deleted_at": None}
            )
        else:
            EnDesktopAffixWord.insert({"affix_id": affix_id, "word_id": word_id}, commit=False)
        db.session.commit()
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def remove_word(affix_id: int, word_id: int) -> dict:
    try:
        EnDesktopAffixWord.delete_by({"affix_id": affix_id, "word_id": word_id})
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)
