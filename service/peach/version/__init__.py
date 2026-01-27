# service/peach/version/__init__.py
"""
版本服务模块 - 使用ORM
"""
from flask import request, jsonify
from app.app import db
from model.peach import Version


def add_version():
    """增加版本"""
    data = request.get_json()
    version = data.get("version")
    name = data.get("name")
    platform = data.get("platform")

    try:
        # 检查是否已存在
        existing = Version.query.filter(
            Version.name == name, Version.platform == platform, Version.deleted_at.is_(None)
        ).first()

        if existing:
            # 更新版本
            version_data = {"id": existing.id, "version": version}
            Version.update(version_data)
        else:
            # 插入新版本
            version_data = {"version": version, "name": name, "platform": platform}
            Version.insert(version_data)

        return jsonify({"code": 200, "msg": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "msg": str(e)})


def list_version():
    """查询版本列表"""
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
        total = Version.count(criterion)

        # 获取分页数据
        offset = (page - 1) * size
        versions = Version.builder_query(criterion).offset(offset).limit(size).all()

        data_list = []
        for item in versions:
            data_list.append(
                {
                    "id": item.id,
                    "version": item.version,
                    "name": item.name,
                    "platform": item.platform,
                }
            )

        return jsonify({"code": 200, "data": {"data": data_list, "total": total, "page": page}})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})
