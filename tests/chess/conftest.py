"""
Chess 模块测试夹具：使用内存 SQLite 替代真实 MySQL。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
