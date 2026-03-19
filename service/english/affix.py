# service/english/affix.py
"""
词缀服务模块 -
"""
import json
from app.app import db
from app.errors import unexpected_error_response
from model.english.affix import Affix
from utils import try_json_parse


def add(data: dict):
    """增加词缀"""
    name = data.get("name")
    meaning = data.get("meaning")
    similar = data.get("similar")
    cases = data.get("cases")

    try:
        similar_str = ",".join(similar) if isinstance(similar, list) else similar
        cases_str = json.dumps(cases, ensure_ascii=False) if cases else None

        affix_data = {
            "name": name,
            "meaning": meaning,
            "similar": similar_str,
            "cases": cases_str,
        }
        Affix.insert(affix_data)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete(data: dict):
    """删除词缀"""
    affix_id = data.get("id")
    try:
        Affix.delete(affix_id)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update(data: dict):
    """更新词缀"""
    name = data.get("name")
    meaning = data.get("meaning")
    similar = data.get("similar")
    cases = data.get("cases")
    affix_id = data.get("id")

    try:
        similar_str = ",".join(similar) if isinstance(similar, list) else similar
        cases_str = json.dumps(cases, ensure_ascii=False) if cases else None

        affix_data = {
            "id": affix_id,
            "name": name,
            "meaning": meaning,
            "similar": similar_str,
            "cases": cases_str,
        }
        Affix.update(affix_data)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def list_affixes(data: dict | None = None):
    """查询词缀列表"""
    try:
        affixes = Affix.select_by()
        data_list = []
        for item in affixes:
            data_list.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "meaning": item.meaning,
                    "similar": item.similar.split(",") if item.similar else [],
                    "cases": try_json_parse(item.cases),
                }
            )
        return {
            "code": 200,
            "data": {"data": data_list, "total": len(data_list), "page": 1},
            "msg": "success",
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)
