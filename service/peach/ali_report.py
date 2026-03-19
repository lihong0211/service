# service/peach/ali_report.py
"""
阿里报告服务模块 -
"""
from sqlalchemy import text
from app.app import db
from app.errors import unexpected_error_response
from model.peach import AliRpCheck


def add(data: dict):
    """增加阿里报告"""
    pharmacist = data.get("pharmacist")
    patientSex = data.get("patientSex")
    patientAge = data.get("patientAge")
    primaryDiagnosis = data.get("primaryDiagnosis")
    medicines = data.get("medicines")
    pass_flag = data.get("pass")
    reason = data.get("reason")
    query = data.get("query")
    rpID = data.get("rpID")

    try:
        ali_data = {
            "pharmacist": pharmacist,
            "patientSex": patientSex,
            "patientAge": patientAge,
            "primaryDiagnosis": primaryDiagnosis,
            "medicines": medicines,
            "pass": pass_flag,
            "reason": reason,
            "query": query,
            "rpID": rpID,
            "refuse": 0,
        }
        AliRpCheck.insert(ali_data)
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def get(data: dict | None = None):
    """获取阿里报告"""
    data = data or {}
    rpID = data.get("rpID")

    if not rpID:
        return {"code": 400, "msg": "Missing rpID parameter"}

    try:
        result = AliRpCheck.select_one_by({"rpID": rpID})
        if result:
            return {"code": 200, "msg": "success", "data": {"refuse": result.refuse or 0}}
        return {"code": 200, "msg": "success", "data": {"refuse": 0}}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update(data: dict):
    """更新阿里报告"""
    rpID = data.get("rpID")
    costTime = data.get("costTime")

    try:
        if costTime:
            result = AliRpCheck.select_one_by({"rpID": rpID})
            if result:
                if result.costTime is None or result.costTime > costTime:
                    AliRpCheck.update({"id": result.id, "costTime": costTime})
        else:
            db.session.execute(
                text("UPDATE ali_rp_check SET refuse = refuse + 1 WHERE rpID = :rpID"),
                {"rpID": rpID},
            )
            db.session.commit()
        return {"code": 200, "msg": "success"}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def list(data: dict | None = None):
    """查询阿里报告列表"""
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

        offset = (page - 1) * size
        results = (
            AliRpCheck.builder_query(criterion)
            .with_entities(
                AliRpCheck.id,
                AliRpCheck.pharmacist,
                AliRpCheck.patientSex,
                AliRpCheck.patientAge,
                AliRpCheck.primaryDiagnosis,
                AliRpCheck.medicines,
                AliRpCheck.pass_flag,
                AliRpCheck.reason,
                AliRpCheck.query,
                AliRpCheck.rpID,
                AliRpCheck.refuse,
                AliRpCheck.costTime,
            )
            .offset(offset)
            .limit(size)
            .all()
        )

        data_list = []
        for item in results:
            data_list.append(
                {
                    "id": item[0],
                    "pharmacist": item[1],
                    "patientSex": item[2],
                    "patientAge": item[3],
                    "primaryDiagnosis": item[4],
                    "medicines": item[5],
                    "pass_flag": item[6],
                    "reason": item[7],
                    "query": item[8],
                    "rpID": item[9],
                    "refuse": item[10] or 0,
                    "costTime": item[11],
                }
            )

        return {
            "code": 200,
            "data": {"data": data_list, "total": 1294953, "page": page},
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)
