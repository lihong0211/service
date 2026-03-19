# app/response.py
"""
统一 API 响应：根据 body 中的 code 设置 HTTP 状态码
"""
from fastapi.responses import JSONResponse

MEDIA_JSON_UTF8 = "application/json; charset=utf-8"


def api_response(body: dict) -> JSONResponse:
    """
    将 service 返回的 { code, msg, data? } 转为 JSONResponse，
    并按 code 设置 HTTP 状态码：200 成功，4xx 客户端错误，5xx 服务端错误。
    """
    code = body.get("code", 200)
    if code == 200:
        status_code = 200
    elif 400 <= code < 500:
        status_code = code
    else:
        status_code = 500
    return JSONResponse(
        content=body,
        status_code=status_code,
        media_type=MEDIA_JSON_UTF8,
    )
