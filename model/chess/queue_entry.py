# model/chess/queue_entry.py
"""
匹配队列模型 - chess 数据库
"""
from sqlalchemy import Column, DateTime, Integer

from app.app import Base
from model.common.base_model import BaseModel


class ChessQueueEntry(Base, BaseModel):
    __tablename__ = "chess_queue_entries"
    __bind_key__ = "chess"

    player_id = Column(Integer, nullable=False, comment="棋手 ID")
    joined_at = Column(DateTime(), nullable=False, comment="入队时间")
