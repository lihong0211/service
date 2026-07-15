# model/chess/session.py
"""
登录会话模型 - chess 数据库
"""
from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base
from model.common.base_model import BaseModel


class ChessSession(Base, BaseModel):
    __tablename__ = "chess_sessions"
    __bind_key__ = "chess"

    token = Column(String(36), nullable=False, unique=True, comment="会话令牌")
    player_id = Column(Integer, nullable=False, comment="棋手 ID")
    expires_at = Column(DateTime(), nullable=False, comment="过期时间")
