# service/english/dialogue.py
"""
对话服务模块 -
"""
import json
from app.app import db
from app.errors import unexpected_error_response
from model.english.dialogue import Dialogue
from utils import try_json_parse


def add(data: dict):
    """增加对话"""
    dialogue_data = data.get("dialogue")
    meaning = data.get("meaning")
    words = data.get("words")
    section = data.get("section")

    try:
        dialogue_str = (
            json.dumps(dialogue_data, ensure_ascii=False) if dialogue_data else None
        )
        words_str = json.dumps(words, ensure_ascii=False) if words else None

        dialogue_obj = {
            "dialogue": dialogue_str,
            "meaning": meaning,
            "words": words_str,
            "section": section,
        }
        Dialogue.insert(dialogue_obj)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete(data: dict):
    """删除对话"""
    dialogue_id = data.get("id")
    try:
        Dialogue.delete(dialogue_id)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update(data: dict):
    """更新对话"""
    dialogue_data = data.get("dialogue")
    meaning = data.get("meaning")
    words = data.get("words")
    section = data.get("section")
    dialogue_id = data.get("id")

    try:
        dialogue_str = (
            json.dumps(dialogue_data, ensure_ascii=False) if dialogue_data else None
        )
        words_str = json.dumps(words, ensure_ascii=False) if words else None

        dialogue_obj = {
            "id": dialogue_id,
            "dialogue": dialogue_str,
            "meaning": meaning,
            "words": words_str,
            "section": section,
        }
        Dialogue.update(dialogue_obj)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def list_dialogues(data: dict | None = None):
    """查询对话列表"""
    try:
        dialogues = Dialogue.select_by()
        data_list = []
        for item in dialogues:
            data_list.append(
                {
                    "id": item.id,
                    "dialogue": try_json_parse(item.dialogue),
                    "meaning": item.meaning,
                    "words": try_json_parse(item.words),
                    "section": item.section,
                }
            )
        return {
            "code": 200,
            "data": {"data": data_list, "total": len(data_list), "page": 1},
            "msg": "success",
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)
