# model/affix_model.py
"""
词缀模型
"""
from sqlalchemy import Column, String, Text
from app.app import db
from model.common.my_model import MyModel


class Affix(db.Model, MyModel):
    __tablename__ = 'affix'
    
    name = Column(String(100), nullable=False, comment='词缀名称')
    meaning = Column(String(200), nullable=True, comment='含义')
    similar = Column(String(200), nullable=True, comment='相似词缀')
    cases = Column(Text, nullable=True, comment='案例')


