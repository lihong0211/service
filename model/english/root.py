# model/english/root.py
"""
词根模型
"""
from sqlalchemy import Column, String, Text
from app.app import db
from model.common.base_model import BaseModel


class Root(db.Model, BaseModel):
    __tablename__ = "root"

    name = Column(String(100), nullable=False, comment="词根名称")
    meaning = Column(String(200), nullable=True, comment="含义")
    similar = Column(String(200), nullable=True, comment="相似词根")
    cases = Column(Text, nullable=True, comment="案例")
