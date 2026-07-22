# service/en_desktop/tencent_tts.py
"""
腾讯云语音合成 (TextToVoice) API，用于例句朗读。
签名用腾讯云 API 3.0 的 TC3-HMAC-SHA256（官方通用签名算法，跟具体产品无关）。
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

SERVICE = "tts"
HOST = "tts.tencentcloudapi.com"
ENDPOINT = f"https://{HOST}"
VERSION = "2019-08-23"
ACTION = "TextToVoice"
REGION = "ap-guangzhou"
ALGORITHM = "TC3-HMAC-SHA256"

# PrimaryLanguage: 1=中文（默认），2=英文——例句是英文，必须显式指定，否则按中文合成
PRIMARY_LANGUAGE_ENGLISH = 2

# 默认音色 WeJames（大模型音色，英文男声），免费额度是"大模型音色"那个较小的池子（10万字符）。
# 额度不够时换成 WeJack（101050，精品音色，同样英文男声），走"语音合成-通用"800万字符的大池子。
DEFAULT_VOICE_TYPE = 501008  # WeJames；额度不够切 101050（WeJack）


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _authorization_header(secret_id: str, secret_key: str, payload: str, timestamp: int) -> str:
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

    canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{HOST}\nx-tc-action:{ACTION.lower()}\n"
    signed_headers = "content-type;host;x-tc-action"
    hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_request = "\n".join(
        ["POST", "/", "", canonical_headers, signed_headers, hashed_payload]
    )

    credential_scope = f"{date}/{SERVICE}/tc3_request"
    hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = "\n".join(
        [ALGORITHM, str(timestamp), credential_scope, hashed_canonical_request]
    )

    secret_date = _hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac_sha256(secret_date, SERVICE)
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    return (
        f"{ALGORITHM} Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )


def synthesize_speech(text: str, voice_type: int = DEFAULT_VOICE_TYPE) -> bytes | None:
    """
    调腾讯云语音合成 API（WeJames，voice_type=501008，英文男声），返回 mp3 二进制。
    请求异常、HTTP 报错、返回内容里带 Error（未开通产品/欠费/文本过长等）
    都归一为返回 None，不抛异常——生成脚本按 None 跳过该条例句，不重试。
    """
    secret_id = os.getenv("TENCENTCLOUD_SECRET_ID")
    secret_key = os.getenv("TENCENTCLOUD_SECRET_KEY")
    if not secret_id or not secret_key:
        raise RuntimeError("未配置 TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY")

    timestamp = int(time.time())
    payload = json.dumps(
        {
            "Text": text,
            "SessionId": str(uuid.uuid4()),
            "VoiceType": voice_type,
            "PrimaryLanguage": PRIMARY_LANGUAGE_ENGLISH,
            "Codec": "mp3",
        },
        separators=(",", ":"),
    )
    authorization = _authorization_header(secret_id, secret_key, payload, timestamp)

    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": HOST,
        "X-TC-Action": ACTION,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": VERSION,
        "X-TC-Region": REGION,
    }

    try:
        resp = requests.post(ENDPOINT, headers=headers, data=payload.encode("utf-8"), timeout=10)
    except requests.exceptions.RequestException as e:
        logger.error("腾讯云语音合成请求异常: %s", e)
        return None

    if resp.status_code != 200:
        logger.error("腾讯云语音合成API报错: status=%s", resp.status_code)
        return None

    result = resp.json().get("Response", {})
    if "Error" in result:
        logger.error("腾讯云语音合成API报错: %s", result["Error"])
        return None

    audio_b64 = result.get("Audio")
    if not audio_b64:
        return None
    return base64.b64decode(audio_b64)
