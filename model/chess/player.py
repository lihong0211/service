# model/chess/player.py
"""
棋手模型 - chess 数据库
"""
from sqlalchemy import Column, String

from app.app import Base
from model.common.base_model import BaseModel


class ChessPlayer(Base, BaseModel):
    __tablename__ = "chess_players"
    __bind_key__ = "chess"

    open_id = Column(String(100), nullable=False, comment="登录标识（mock 微信 code 派生）")
    nickname = Column(String(100), nullable=False, comment="昵称")
    avatar_url = Column(String(500), nullable=True, comment="头像地址")
