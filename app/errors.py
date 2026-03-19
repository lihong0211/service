# app/errors.py
"""
统一处理未预期异常：打日志、回滚、返回通用 500 响应体
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def unexpected_error_response(
    exc: Exception,
    session: Session | None = None,
    log: logging.Logger | None = None,
) -> dict[str, Any]:
    """记录异常、可选回滚 session，返回 { code: 500, msg }，不向调用方暴露异常详情。"""
    (log or logger).exception("Unexpected error: %s", exc, exc_info=True)
    if session is not None:
        try:
            session.rollback()
        except Exception:
            pass
    return {"code": 500, "msg": "Internal Server Error"}
