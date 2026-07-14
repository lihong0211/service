# model/chess/room.py
"""
对局房间模型 - chess 数据库
"""
from sqlalchemy import Column, Integer, String

from app.app import Base
from model.common.base_model import BaseModel


class ChessRoom(Base, BaseModel):
    __tablename__ = "chess_rooms"
    __bind_key__ = "chess"

    red_player_id = Column(Integer, nullable=False, comment="红方棋手 ID")
    black_player_id = Column(Integer, nullable=False, comment="黑方棋手 ID")
    fen = Column(String(200), nullable=False, comment="当前局面（含轮走方）")
    turn = Column(String(10), nullable=False, comment="轮走方：red/black")
    status = Column(String(20), nullable=False, comment="对局状态")
