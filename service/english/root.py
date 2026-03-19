# service/english/root.py
"""
词根服务模块 -
"""
import json
from app.app import db
from app.errors import unexpected_error_response
from model.english.root import Root
from utils import try_json_parse


def add(data: dict):
    """增加词根"""
    name = data.get("name")
    meaning = data.get("meaning")
    similar = data.get("similar")
    cases = data.get("cases")

    try:
        similar_str = ",".join(similar) if isinstance(similar, list) else similar
        cases_str = json.dumps(cases, ensure_ascii=False) if cases else None

        root_data = {
            "name": name,
            "meaning": meaning,
            "similar": similar_str,
            "cases": cases_str,
        }
        Root.insert(root_data)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete(data: dict):
    """删除词根"""
    root_id = data.get("id")
    try:
        Root.delete(root_id)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update(data: dict):
    """更新词根"""
    name = data.get("name")
    meaning = data.get("meaning")
    similar = data.get("similar")
    cases = data.get("cases")
    root_id = data.get("id")

    try:
        similar_str = ",".join(similar) if isinstance(similar, list) else similar
        cases_str = json.dumps(cases, ensure_ascii=False) if cases else None

        root_data = {
            "id": root_id,
            "name": name,
            "meaning": meaning,
            "similar": similar_str,
            "cases": cases_str,
        }
        Root.update(root_data)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def list_roots(data: dict | None = None):
    """查询词根列表"""
    try:
        roots = Root.select_by()
        data_list = []
        for item in roots:
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
