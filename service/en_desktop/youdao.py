# service/en_desktop/youdao.py
"""
有道智云文本翻译 API
"""
import hashlib
import logging
import os
import time
import uuid

import requests

logger = logging.getLogger(__name__)

YOUDAO_API_URL = "https://openapi.youdao.com/api"


def _truncate(q: str) -> str:
    if len(q) <= 20:
        return q
    return q[:10] + str(len(q)) + q[-10:]


def _sign(app_key: str, app_secret: str, q: str, salt: str, curtime: str) -> str:
    raw = app_key + _truncate(q) + salt + curtime + app_secret
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def translate_to_chinese(text: str) -> str:
    """
    英文文本翻成中文，返回翻译文本；请求/接口出错时返回空字符串
    """
    app_key = os.getenv("YOUDAO_APP_KEY")
    app_secret = os.getenv("YOUDAO_APP_SECRET")
    if not app_key or not app_secret:
        raise RuntimeError("未配置 YOUDAO_APP_KEY / YOUDAO_APP_SECRET")

    salt = str(uuid.uuid4())
    curtime = str(int(time.time()))
    sign = _sign(app_key, app_secret, text, salt, curtime)

    resp = requests.post(
        YOUDAO_API_URL,
        data={
            "q": text,
            "from": "en",
            "to": "zh-CHS",
            "appKey": app_key,
            "salt": salt,
            "sign": sign,
            "signType": "v3",
            "curtime": curtime,
        },
        timeout=5,
    )
    data = resp.json()

    if data.get("errorCode") != "0":
        logger.error("有道翻译API报错: %s", data)
        return ""

    translation = data.get("translation") or []
    return translation[0] if translation else ""
