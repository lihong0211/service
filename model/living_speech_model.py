# model/living_speech_model.py
"""
生活用语模型
"""
from sqlalchemy import Column, String, Text
from app.app import db
from model.common.my_model import MyModel


class LivingSpeech(db.Model, MyModel):
    __tablename__ = 'livingSpeech'
    
    speech = Column(String(200), nullable=False, comment='用语')
    meaning = Column(String(200), nullable=True, comment='含义')


