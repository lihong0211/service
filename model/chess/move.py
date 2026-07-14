# model/chess/move.py
"""
着法记录模型 - chess 数据库
"""
from sqlalchemy import Column, Integer, String

from app.app import Base
from model.common.base_model import BaseModel


class ChessMove(Base, BaseModel):
    __tablename__ = "chess_moves"
    __bind_key__ = "chess"

    room_id = Column(Integer, nullable=False, comment="所属房间 ID")
    seq = Column(Integer, nullable=False, comment="着法序号，从 1 开始")
    color = Column(String(10), nullable=False, comment="走子方：red/black")
    from_row = Column(Integer, nullable=False)
    from_col = Column(Integer, nullable=False)
    to_row = Column(Integer, nullable=False)
    to_col = Column(Integer, nullable=False)
    piece = Column(String(20), nullable=False, comment="棋子类型")
    captured = Column(String(20), nullable=True, comment="被吃棋子类型")
    iccs = Column(String(10), nullable=False, comment="ICCS 记谱")
