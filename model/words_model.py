# model/words_model.py
"""
单词模型
"""
from sqlalchemy import Column, String, Text, Integer
from app.app import db
from model.common.my_model import MyModel


class Words(db.Model, MyModel):
    __tablename__ = "words"

    word = Column(String(100), nullable=False, comment="单词")
    type = Column(String(100), nullable=True, comment="类型")
    meaning = Column(Text, nullable=True, comment="含义")
    root = Column(String(100), nullable=True, comment="词根")
    root_case = Column(String(200), nullable=True, comment="词根案例")
    affix = Column(String(100), nullable=True, comment="词缀")
    affix_case = Column(String(200), nullable=True, comment="词缀案例")
    collocation = Column(String(200), nullable=True, comment="搭配")
    collocation_meaning = Column(String(200), nullable=True, comment="搭配含义")
    sentence = Column(Text, nullable=True, comment="例句")
    mastered = Column(Integer(), default=0, comment="是否掌握")

