# model/english/living_speech.py
"""
生活用语模型
"""
from sqlalchemy import Column, String, Text
from app.app import db
from model.common.base_model import BaseModel


class LivingSpeech(db.Model, BaseModel):
    __tablename__ = "livingSpeech"

    speech = Column(String(200), nullable=False, comment="用语")
    meaning = Column(String(200), nullable=True, comment="含义")
