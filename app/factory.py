# app/factory.py
"""
应用工厂：路由、异常处理、请求日志；DB 通过路由级 Depends(get_db) 绑定请求 session。
"""
import logging
import time

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import get_db
from config.db import DB_EN_CONFIG

logger = logging.getLogger(__name__)


def _validate_db_config() -> None:
    if not DB_EN_CONFIG.get("user"):
        raise ValueError("请配置数据库用户：DB_USER 或环境变量（.env）")
    if not DB_EN_CONFIG.get("password"):
        raise ValueError("请配置数据库密码：DB_PASSWORD（.env）")


def _http_exception_payload(exc: HTTPException) -> dict:
    detail = exc.detail
    if isinstance(detail, str):
        return {"code": exc.status_code, "msg": detail}
    if isinstance(detail, list):
        return {"code": exc.status_code, "msg": "Request error", "data": detail}
    if isinstance(detail, dict):
        return {"code": exc.status_code, "msg": detail.get("msg", "Error"), "data": detail}
    return {"code": exc.status_code, "msg": "Error"}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            content=_http_exception_payload(exc),
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "msg": "参数校验失败",
                "data": exc.errors(),
            },
        )

    @app.exception_handler(FileNotFoundError)
    async def handle_file_not_found(request: Request, exc: FileNotFoundError):
        return JSONResponse(content={"code": 404, "msg": str(exc)}, status_code=404)

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError):
        return JSONResponse(content={"code": 400, "msg": str(exc)}, status_code=400)

    @app.exception_handler(Exception)
    async def handle_exception(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            content={"code": 500, "msg": "Internal Server Error"},
            status_code=500,
        )


def create_app() -> FastAPI:
    _validate_db_config()

    app = FastAPI(
        title="service-ali",
        description="API 服务",
    )

    register_exception_handlers(app)

    # Electron 桌面客户端打包后是 file:// 页面直连本服务（IP:port，暂无域名/nginx），
    # 属于真跨域请求；认证走 Bearer token 不用 cookie，允许全部来源没有 CSRF 风险
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from routes import api_router

    app.include_router(api_router, dependencies=[Depends(get_db)])

    @app.middleware("http")
    async def request_log_middleware(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        logger.info(
            "%s %s %s %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response

    return app
