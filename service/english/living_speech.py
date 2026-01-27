# service/english/living_speech.py
"""
生活用语服务模块 -
"""
from flask import request, jsonify
from app.app import db
from model.english.living_speech import LivingSpeech


def add():
    """增加生活用语"""
    data = request.get_json()
    speech = data.get("speech")
    meaning = data.get("meaning")

    try:
        speech_data = {
            "speech": speech,
            "meaning": meaning,
        }
        LivingSpeech.insert(speech_data)

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
    """删除生活用语"""
    data = request.get_json()
    speech_id = data.get("id")

    try:
        LivingSpeech.delete(speech_id)
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
    """更新生活用语"""
    data = request.get_json()
    speech = data.get("speech")
    meaning = data.get("meaning")
    speech_id = data.get("id")

    try:
        speech_data = {
            "id": speech_id,
            "speech": speech,
            "meaning": meaning,
        }
        LivingSpeech.update(speech_data)

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


def list_speeches():
    """查询生活用语列表"""
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
        total = LivingSpeech.count(criterion)

        # 获取分页数据
        offset = (page - 1) * size
        speeches = (
            LivingSpeech.builder_query(criterion).offset(offset).limit(size).all()
        )

        data_list = []
        for item in speeches:
            data_list.append(
                {
                    "id": item.id,
                    "speech": item.speech,
                    "meaning": item.meaning,
                }
            )

        return jsonify(
            {
                "code": 200,
                "data": {
                    "data": data_list,
                    "total": total,
                    "page": page,
                },
            }
        )
    except Exception as e:
        return jsonify(
            {
                "code": 500,
                "msg": str(e),
            }
        )
