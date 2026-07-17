"""
en-desktop 模块测试夹具：内存 SQLite 替代真实 MySQL。
模块用独立的 BaseEnDesktop（避免与 english 模块的 words 表名冲突），
建表用它自己的 metadata。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import clear_request_session, set_request_session
from model.en_desktop import BaseEnDesktop


@pytest.fixture
def en_desktop_db():
    engine = create_engine("sqlite:///:memory:")
    BaseEnDesktop.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    set_request_session(session)
    try:
        yield session
    finally:
        clear_request_session()
        session.close()
        engine.dispose()
