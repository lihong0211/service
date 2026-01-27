# service/english/dialogue.py
"""
对话服务模块 -
"""
import json
from flask import request, jsonify
from app.app import db
from model.english.dialogue import Dialogue
from utils import try_json_parse


def add():
    """增加对话"""
    data = request.get_json()
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

        return jsonify(
            {
                "code": 200,
                "msg": "success",
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {
                "code": 500,
                "msg": str(e),
            }
        )


def delete():
    """删除对话"""
    data = request.get_json()
    dialogue_id = data.get("id")

    try:
        Dialogue.delete(dialogue_id)
        return jsonify(
            {
                "code": 200,
                "msg": "success",
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {
                "code": 500,
                "msg": str(e),
            }
        )


def update():
    """更新对话"""
    data = request.get_json()
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

        return jsonify(
            {
                "code": 200,
                "msg": "success",
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {
                "code": 500,
                "msg": str(e),
            }
        )


def list_dialogues():
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

        return jsonify(
            {
                "code": 200,
                "data": {
                    "data": data_list,
                    "total": len(data_list),
                    "page": 1,
                },
                "msg": "success",
            }
        )
    except Exception as e:
        return jsonify(
            {
                "code": 500,
                "msg": str(e),
            }
        )
