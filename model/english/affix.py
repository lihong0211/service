# model/english/affix.py
"""
词缀模型
"""
from sqlalchemy import Column, String, Text
from app.app import db
from model.common.base_model import BaseModel


class Affix(db.Model, BaseModel):
    __tablename__ = "affix"

    name = Column(String(100), nullable=False, comment="词缀名称")
    meaning = Column(String(200), nullable=True, comment="含义")
    similar = Column(String(200), nullable=True, comment="相似词缀")
    cases = Column(Text, nullable=True, comment="案例")
