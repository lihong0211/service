# service/peach/config/__init__.py
"""
配置服务模块 - 使用ORM
"""
from flask import jsonify
from model.peach import Config


def list_config():
    """查询配置列表"""
    try:
        configs = Config.select_by()

        data_list = []
        for item in configs:
            data_list.append(
                {
                    "id": item.id,
                    "key": item.key,
                    "value": item.value,
                    "description": item.description,
                }
            )

        return jsonify(
            {
                "code": 200,
                "data": {"data": data_list, "total": len(data_list)},
                "msg": "success",
            }
        )
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})
