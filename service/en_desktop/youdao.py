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

# 有道词典公开 JSON 接口（未鉴权，不需要 APP_KEY/APP_SECRET）。跟 en-elctron 客户端
# 播放单词发音用的 dict.youdao.com/dictvoice 是同一个域名下的公开服务，type=1/type=2
# 音频分别对应这里的 ukphone/usphone。openapi.youdao.com 的官方翻译 API 不返回音标
# （isWord 字段为 false），所以音标走这个接口。
YOUDAO_DICT_JSONAPI_URL = "https://dict.youdao.com/jsonapi"


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


def fetch_phonetic(word: str) -> dict | None:
    """
    查有道词典拿真正区分英式/美式的音标（不查释义，不需要鉴权）。
    返回结构：{"en_pronunciation"（英式）, "us_pronunciation"（美式）}，
    查不到词条或没有音标字段时返回 None。
    """
    resp = requests.get(YOUDAO_DICT_JSONAPI_URL, params={"q": word}, timeout=5)
    if resp.status_code != 200:
        return None

    words = (resp.json().get("ec") or {}).get("word") or []
    if not words:
        return None

    entry = words[0]
    ukphone, usphone = entry.get("ukphone"), entry.get("usphone")
    if not ukphone or not usphone:
        return None
    return {"en_pronunciation": ukphone, "us_pronunciation": usphone}
