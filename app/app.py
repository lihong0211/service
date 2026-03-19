# app/app.py
"""
FastAPI 应用初始化 + SQLAlchemy（替代 Flask-SQLAlchemy）
"""
import logging
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config.db import DB_EN_CONFIG, DB_PDD_CONFIG

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 数据库引擎（主库 + PDD 从库）
# ---------------------------------------------------------------------------
_en_mysql_url = (
    f"mysql+pymysql://{DB_EN_CONFIG['user']}:{DB_EN_CONFIG['password']}"
    f"@{DB_EN_CONFIG['host']}:{DB_EN_CONFIG['port']}/{DB_EN_CONFIG['database']}"
    f"?charset={DB_EN_CONFIG.get('charset', 'utf8mb4')}"
)

_pdd_mysql_url = (
    f"mysql+pymysql://{DB_PDD_CONFIG['user']}:{DB_PDD_CONFIG['password']}"
    f"@{DB_PDD_CONFIG['host']}:{DB_PDD_CONFIG['port']}/{DB_PDD_CONFIG['database']}"
    f"?charset={DB_PDD_CONFIG.get('charset', 'utf8mb4')}"
)

engine_en = create_engine(
    _en_mysql_url,
    pool_size=50,
    max_overflow=200,
    pool_recycle=3600,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)

engine_pdd = create_engine(
    _pdd_mysql_url,
    pool_size=50,
    max_overflow=200,
    pool_recycle=3600,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)

# ---------------------------------------------------------------------------
# 声明基类（替代 db.Model）
# ---------------------------------------------------------------------------
Base = declarative_base()


# ---------------------------------------------------------------------------
# 多数据源路由 Session
# ---------------------------------------------------------------------------
class _RoutingSession(Session):
    def get_bind(self, mapper=None, clause=None):
        if mapper is not None:
            bind_key = getattr(mapper.class_, "__bind_key__", None)
            if bind_key == "pdd":
                return engine_pdd
        return engine_en


SessionLocal = sessionmaker(
    class_=_RoutingSession,
    autocommit=False,
    autoflush=False,
    bind=engine_en,
)

# ---------------------------------------------------------------------------
# 请求级 session：通过 ContextVar 在请求内共享同一 session
# ---------------------------------------------------------------------------
_db_session_ctx: ContextVar[Session | None] = ContextVar("db_session", default=None)


class _DbProxy:
    """对外仍使用 db.session，实际从当前请求的 ContextVar 取 session"""

    @property
    def session(self) -> Session:
        s = _db_session_ctx.get()
        if s is None:
            raise RuntimeError(
                "db.session 仅在请求上下文中可用，请确保已挂载 DB 中间件"
            )
        return s


db = _DbProxy()


def get_db():
    """FastAPI 依赖：获取当前请求的 DB Session（与中间件设置的 ContextVar 一致）"""
    session = _db_session_ctx.get()
    if session is None:
        raise RuntimeError("db session 未在请求上下文中设置")
    return session


# ---------------------------------------------------------------------------
# FastAPI 应用
# ---------------------------------------------------------------------------
app = FastAPI(
    title="service-ali",
    description="API 服务",
)


from routes import api_router

app.include_router(api_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            content={"code": 404, "msg": "Not Found"},
            status_code=404,
            media_type="application/json; charset=utf-8",
        )
    return JSONResponse(
        content={"code": exc.status_code, "msg": exc.detail or "Error"},
        status_code=exc.status_code,
        media_type="application/json; charset=utf-8",
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        content={"code": 500, "msg": "Internal Server Error"},
        status_code=500,
        media_type="application/json; charset=utf-8",
    )


@app.middleware("http")
async def db_session_middleware(request, call_next):
    session = SessionLocal()
    token = _db_session_ctx.set(session)
    try:
        response = await call_next(request)
        return response
    finally:
        _db_session_ctx.reset(token)
        session.close()


@app.middleware("http")
async def request_log_middleware(request, call_next):
    import time

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
