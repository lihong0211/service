"""
Chess 模块测试夹具：使用内存 SQLite 替代真实 MySQL。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Must fully import app.app before touching the bare `model` package: model/__init__.py
# eagerly imports model.english, which imports app.app, which (via create_app()) imports
# service.english.words, which imports model.english.words again. That only resolves if
# app.app is already fully loaded first (true in production, where main.py imports it
# before anything else) — otherwise it's a circular partial-init ImportError.
import app.app  # noqa: F401
from app.database import Base, clear_request_session, set_request_session
from model.chess import ChessMove, ChessPlayer, ChessQueueEntry, ChessRoom, ChessSession

CHESS_TABLES = [
    ChessPlayer.__table__,
    ChessSession.__table__,
    ChessRoom.__table__,
    ChessMove.__table__,
    ChessQueueEntry.__table__,
]


@pytest.fixture
def chess_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=CHESS_TABLES)
    session = sessionmaker(bind=engine)()
    set_request_session(session)
    try:
        yield session
    finally:
        clear_request_session()
        session.close()
        engine.dispose()
