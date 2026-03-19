# utils/__init__.py
"""
工具函数模块
"""


def try_json_parse(data):
    """尝试解析 JSON 字符串，解析失败返回 []。"""
    import json

    if data is None:
        return []
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return []
    return data
