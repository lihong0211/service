# service/peach/check/__init__.py
"""
检查服务模块 - 使用ORM
"""
from flask import request, jsonify
from app.app import db
from model.peach import CheckReport


def add():
    """增加检查记录"""
    data = request.get_json()
    platform = data.get("platform")
    patientSex = data.get("patientSex")
    patientAge = data.get("patientAge")
    primaryDiagnosis = data.get("primaryDiagnosis")
    medicines = data.get("medicines")
    pass_flag = data.get("pass")
    params = data.get("params")
    error = data.get("error")
    isNotMatch = data.get("isNotMatch")
    doctor = data.get("doctor")
    medicineName = data.get("fullName")
    specification = data.get("specification")
    takeDirection = data.get("takeDirection")
    takeFrequence = data.get("takeFrequence")
    medicineAmount = data.get("medicineAmount")
    takeDose = data.get("takeDose")
    formType = data.get("formType")

    if not all([medicineName, specification, takeDirection, takeFrequence, takeDose, formType]):
        return jsonify({"code": 500, "msg": "缺少参数"})

    try:
        check_data = {
            "platform": platform,
            "patientSex": patientSex,
            "patientAge": patientAge,
            "primaryDiagnosis": primaryDiagnosis,
            "medicines": medicines,
            "pass_flag": pass_flag,
            "params": params,
            "error": error,
            "isNotMatch": isNotMatch,
            "doctor": doctor,
            "medicineName": medicineName,
            "specification": specification,
            "takeDirection": takeDirection,
            "takeFrequence": takeFrequence,
            "medicineAmount": medicineAmount,
            "takeDose": takeDose,
            "formType": formType,
        }
        CheckReport.insert(check_data)

        return jsonify({"code": 200, "msg": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "msg": str(e)})
