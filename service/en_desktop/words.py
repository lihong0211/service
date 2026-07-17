# service/en_desktop/words.py
"""
en-desktop 单词服务：CRUD + 查词（词典 API + 有道翻译）
"""
from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import EnDesktopWord, EnDesktopWordMeaning
from service.en_desktop import dictionary
from service.en_desktop import libraries as libraries_service


def _meanings_of(word_id: int) -> list:
    meanings = EnDesktopWordMeaning.select_by({"word_id": word_id})
    return [{"type": m.type, "content": m.content} for m in meanings]


def _word_with_meanings(word: EnDesktopWord) -> dict:
    return word.to_dict(meaning=_meanings_of(word.id))


def _replace_meanings(word_id: int, meaning: list) -> None:
    """全量替换释义（软删旧的再插新的），不提交事务"""
    EnDesktopWordMeaning.delete_by({"word_id": word_id}, commit=False)
    for item in meaning:
        EnDesktopWordMeaning.insert(
            {"word_id": word_id, "type": item.get("type"), "content": item.get("content")},
            commit=False,
        )


def list_words(page: int = 1, page_size: int = 10) -> dict:
    try:
        words = EnDesktopWord.select_by()
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "code": 200,
            "msg": "success",
            "data": [_word_with_meanings(w) for w in words[start:end]],
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def get_word(word_id: int) -> dict:
    try:
        word = EnDesktopWord.get_by_id(word_id)
        if not word:
            return {"code": 500, "msg": "单词不存在"}
        return {"code": 200, "msg": "success", "data": _word_with_meanings(word)}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_word(data: dict, user_id: int | None = None) -> dict:
    """
    创建单词。可选 library_id（数字 ID 或 "default"=我的收藏）：
    单词入全局表的同时加进该词库（已存在的单词只加词库，幂等），需要登录。
    不传 library_id 时行为与原桌面端后端一致。
    """
    word_text = (data.get("word") or "").strip()
    en_pronunciation = data.get("en_pronunciation") or ""
    us_pronunciation = data.get("us_pronunciation") or ""
    meaning = data.get("meaning") or []
    library_id = data.get("library_id")

    if not word_text or len(word_text) > 30:
        return {"code": 400, "msg": "word 不能为空且不超过30个字符"}
    if not en_pronunciation or not us_pronunciation:
        return {"code": 400, "msg": "en_pronunciation / us_pronunciation 不能为空"}
    if library_id and user_id is None:
        return {"code": 401, "msg": "未登录或登录已过期"}

    try:
        existing = EnDesktopWord.select_one_by({"word": word_text})
        if existing and not library_id:
            return {"code": 500, "msg": "单词已存在"}

        if existing:
            word_id = existing.id
        else:
            word_id = EnDesktopWord.insert(
                {
                    "word": word_text,
                    "en_pronunciation": en_pronunciation,
                    "us_pronunciation": us_pronunciation,
                },
                commit=False,
            )
            _replace_meanings(word_id, meaning)

        if library_id:
            if library_id == "default":
                library_id = libraries_service.ensure_default_library(user_id).id
            elif not libraries_service.owned_library(user_id, library_id):
                db.session.rollback()
                return {"code": 400, "msg": "词库不存在"}
            # 已在词库中视为收藏成功（幂等）
            libraries_service.add_item(library_id, word_id)

        db.session.commit()

        return {
            "code": 200,
            "msg": "success",
            "data": _word_with_meanings(EnDesktopWord.get_by_id(word_id)),
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def lookup(data: dict) -> dict:
    """查词，不自动存库；saved 标记该词是否已在库中"""
    word_text = (data.get("word") or "").strip()
    if not word_text:
        return {"code": 400, "msg": "word 不能为空"}

    try:
        result = dictionary.lookup_word(word_text)
    except RuntimeError as e:
        return {"code": 500, "msg": str(e)}
    except Exception as e:
        return unexpected_error_response(e)

    if not result:
        return {"code": 500, "msg": "查询不到这个单词"}

    try:
        existing = EnDesktopWord.select_one_by({"word": result["word"]})
        result["saved"] = existing is not None
        return {"code": 200, "msg": "success", "data": result}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update_word(word_id: int, data: dict) -> dict:
    try:
        existing = EnDesktopWord.get_by_id(word_id)
        if not existing:
            return {"code": 500, "msg": "单词不存在"}

        update_dict = {
            key: data[key]
            for key in ("word", "en_pronunciation", "us_pronunciation")
            if key in data and data[key] is not None
        }

        new_word = update_dict.get("word")
        if new_word and new_word != existing.word:
            dup = EnDesktopWord.select_one_by({"word": new_word})
            if dup and dup.id != word_id:
                return {"code": 500, "msg": "单词已存在"}

        if update_dict:
            update_dict["id"] = word_id
            EnDesktopWord.update(update_dict, commit=False)

        if data.get("meaning") is not None:
            _replace_meanings(word_id, data["meaning"])

        db.session.commit()
        return {
            "code": 200,
            "msg": "success",
            "data": _word_with_meanings(EnDesktopWord.get_by_id(word_id)),
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete_word(word_id: int) -> dict:
    try:
        EnDesktopWord.delete(word_id)
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)
