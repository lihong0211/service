# service/english/living_speech.py
"""
生活用语服务模块 -
"""
from app.app import db
from app.errors import unexpected_error_response
from model.english.living_speech import LivingSpeech


def add(data: dict):
    """增加生活用语"""
    speech = data.get("speech")
    meaning = data.get("meaning")

    try:
        speech_data = {"speech": speech, "meaning": meaning}
        LivingSpeech.insert(speech_data)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete(data: dict):
    """删除生活用语"""
    speech_id = data.get("id")
    try:
        LivingSpeech.delete(speech_id)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update(data: dict):
    """更新生活用语"""
    speech = data.get("speech")
    meaning = data.get("meaning")
    speech_id = data.get("id")

    try:
        speech_data = {"id": speech_id, "speech": speech, "meaning": meaning}
        LivingSpeech.update(speech_data)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def list_speeches(data: dict | None = None):
    """查询生活用语列表"""
    data = data or {}
    page = data.get("page", 1)
    size = data.get("size", 10)
    query = data.get("query")

    try:
        criterion = {}
        if query:
            for key, value in query.items():
                if value:
                    criterion[key] = {"type": "like", "value": value}

        total = LivingSpeech.count(criterion)
        offset = (page - 1) * size
        speeches = (
            LivingSpeech.builder_query(criterion).offset(offset).limit(size).all()
        )

        data_list = []
        for item in speeches:
            data_list.append(
                {"id": item.id, "speech": item.speech, "meaning": item.meaning}
            )

        return {
            "code": 200,
            "data": {"data": data_list, "total": total, "page": page},
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)
