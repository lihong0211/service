# app/database.py
"""
FastAPI + SQLAlchemy：主库 EN + PDD 从库（__bind_key__=\"pdd\"）。
请求级 session 由 get_db 注入并在 ContextVar 中供 db.session 使用。
"""
from collections.abc import AsyncGenerator
from contextvars import ContextVar

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config.db import DB_CHESS_CONFIG, DB_EN_CONFIG, DB_PDD_CONFIG

Base = declarative_base()

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

_chess_mysql_url = (
    f"mysql+pymysql://{DB_CHESS_CONFIG['user']}:{DB_CHESS_CONFIG['password']}"
    f"@{DB_CHESS_CONFIG['host']}:{DB_CHESS_CONFIG['port']}/{DB_CHESS_CONFIG['database']}"
    f"?charset={DB_CHESS_CONFIG.get('charset', 'utf8mb4')}"
)

engine_en: Engine = create_engine(
    _en_mysql_url,
    pool_size=50,
    max_overflow=200,
    pool_recycle=3600,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)

engine_pdd: Engine = create_engine(
    _pdd_mysql_url,
    pool_size=50,
    max_overflow=200,
    pool_recycle=3600,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)

engine_chess: Engine = create_engine(
    _chess_mysql_url,
    pool_size=50,
    max_overflow=200,
    pool_recycle=3600,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)

engines: dict[str, Engine] = {"en": engine_en, "pdd": engine_pdd, "chess": engine_chess}


class _RoutingSession(Session):
    def get_bind(self, mapper=None, clause=None):
        if mapper is not None:
            bind_key = getattr(mapper.class_, "__bind_key__", None)
            if bind_key == "pdd":
                return engine_pdd
            if bind_key == "chess":
                return engine_chess
        return engine_en


SessionLocal = sessionmaker(
    class_=_RoutingSession,
    autocommit=False,
    autoflush=False,
    bind=engine_en,
)

_session_ctx: ContextVar[Session | None] = ContextVar("sqlalchemy_session", default=None)


def set_request_session(session: Session) -> None:
    _session_ctx.set(session)


def clear_request_session() -> None:
    _session_ctx.set(None)


async def get_db() -> AsyncGenerator[Session, None]:
    session = SessionLocal()
    _session_ctx.set(session)
    try:
        yield session
    finally:
        _session_ctx.set(None)
        session.close()


class _DbCompat:
    @property
    def Model(self):
        return Base

    @property
    def session(self) -> Session:
        s = _session_ctx.get()
        if s is None:
            raise RuntimeError(
                "No request-scoped session. Use router dependencies=[Depends(get_db)] or set_request_session."
            )
        return s

    @property
    def engine(self) -> Engine:
        return engine_en

    @property
    def engines(self) -> dict[str, Engine]:
        return engines


db = _DbCompat()
