# model/english/dialogue.py
"""
对话模型
"""
from sqlalchemy import Column, String, Text
from app.app import db
from model.common.base_model import BaseModel


class Dialogue(db.Model, BaseModel):
    __tablename__ = "dialogue"

    dialogue = Column(Text, nullable=True, comment="对话内容")
    meaning = Column(String(200), nullable=True, comment="含义")
    words = Column(Text, nullable=True, comment="单词")
    section = Column(String(100), nullable=True, comment="章节")
