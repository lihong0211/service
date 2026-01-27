# service/peach/pddReport/__init__.py
"""
拼多多报告服务模块 - 使用ORM
"""
import json
from flask import request, jsonify
from app.app import db
from model.peach import Chat, Rp, Manual


def add_chat():
    """增加聊天记录"""
    data = request.get_json()
    sessionid = data.get("sessionid")
    req_content = data.get("req_content")
    res_content = data.get("res_content")
    cost = data.get("cost")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    try:
        req_content_str = json.dumps(req_content, ensure_ascii=False) if req_content else None
        res_content_str = json.dumps(res_content, ensure_ascii=False) if res_content else None

        chat_data = {
            "sessionid": sessionid,
            "req_content": req_content_str,
            "res_content": res_content_str,
            "cost": cost,
            "start_time": start_time,
            "end_time": end_time,
        }
        Chat.insert(chat_data)

        return jsonify({"code": 200, "msg": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "msg": str(e)})


def list_chat():
    """查询聊天记录列表"""
    data = request.get_json() if request.is_json else {}
    page = data.get("page", 1)
    size = data.get("size", 10)
    query = data.get("query")

    try:
        # 构建查询条件
        criterion = {}
        if query:
            for key, value in query.items():
                if value:
                    criterion[key] = {"type": "like", "value": value}

        # 获取总数
        total = Chat.count(criterion)

        # 获取分页数据
        offset = (page - 1) * size
        chats = Chat.builder_query(criterion).offset(offset).limit(size).all()

        data_list = []
        for item in chats:
            data_list.append(
                {
                    "id": item.id,
                    "sessionid": item.sessionid,
                    "req_content": item.req_content,
                    "res_content": item.res_content,
                    "cost": item.cost,
                    "start_time": item.start_time.isoformat() if item.start_time else None,
                    "end_time": item.end_time.isoformat() if item.end_time else None,
                }
            )

        return jsonify({"code": 200, "data": {"data": data_list, "total": total, "page": page}})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})


def add_rp():
    """增加处方记录"""
    data = request.get_json()
    sessionid = data.get("sessionid")
    name = data.get("name")
    sex = data.get("sex")
    age = data.get("age")
    pddDiagnosis = data.get("pddDiagnosis")
    recommendDiagnosis = data.get("recommendDiagnosis")
    medicine = data.get("medicine")
    dosage = data.get("dosage")
    time = data.get("time")
    diagnosis = data.get("diagnosis")

    try:
        rp_data = {
            "sessionid": sessionid,
            "name": name,
            "age": age,
            "sex": sex,
            "pddDiagnosis": pddDiagnosis or diagnosis,
            "recommendDiagnosis": recommendDiagnosis,
            "medicine": medicine,
            "dosage": dosage,
            "time": time,
        }
        Rp.insert(rp_data)

        return jsonify({"code": 200, "msg": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "msg": str(e)})


def list_rp():
    """查询处方记录列表"""
    data = request.get_json() if request.is_json else {}
    page = data.get("page", 1)
    size = data.get("size", 10)
    query = data.get("query")

    try:
        # 构建查询条件
        criterion = {}
        if query:
            for key, value in query.items():
                if value:
                    criterion[key] = {"type": "like", "value": value}

        # 获取总数
        total = Rp.count(criterion)

        # 获取分页数据
        offset = (page - 1) * size
        rps = Rp.builder_query(criterion).offset(offset).limit(size).all()

        data_list = []
        for item in rps:
            data_list.append(
                {
                    "id": item.id,
                    "sessionid": item.sessionid,
                    "name": item.name,
                    "age": item.age,
                    "sex": item.sex,
                    "pddDiagnosis": item.pddDiagnosis,
                    "recommendDiagnosis": item.recommendDiagnosis,
                    "medicine": item.medicine,
                    "dosage": item.dosage,
                    "time": item.time.isoformat() if item.time else None,
                }
            )

        return jsonify({"code": 200, "data": {"data": data_list, "total": total, "page": page}})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})


def add_manual():
    """增加手动记录"""
    data = request.get_json()
    sessionid = data.get("sessionid")
    manual_type = data.get("type")
    time = data.get("time")
    session_data = data.get("session_data")

    try:
        session_data_str = ""
        if session_data and isinstance(session_data, dict):
            session_data_str = json.dumps(session_data, ensure_ascii=False)

        manual_data = {
            "sessionid": sessionid,
            "type": manual_type,
            "time": time,
            "session_data": session_data_str,
        }
        Manual.insert(manual_data)

        return jsonify({"code": 200, "msg": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "msg": str(e)})


def list_manual():
    """查询手动记录列表"""
    data = request.get_json() if request.is_json else {}
    page = data.get("page", 1)
    size = data.get("size", 10)
    query = data.get("query")

    try:
        # 构建查询条件
        criterion = {}
        if query:
            for key, value in query.items():
                if value:
                    criterion[key] = {"type": "like", "value": value}

        # 获取总数
        total = Manual.count(criterion)

        # 获取分页数据
        offset = (page - 1) * size
        manuals = Manual.builder_query(criterion).offset(offset).limit(size).all()

        data_list = []
        for item in manuals:
            data_list.append(
                {
                    "id": item.id,
                    "sessionid": item.sessionid,
                    "type": item.type,
                    "time": item.time.isoformat() if item.time else None,
                    "session_data": item.session_data,
                }
            )

        return jsonify({"code": 200, "data": {"data": data_list, "total": total, "page": page}})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})
