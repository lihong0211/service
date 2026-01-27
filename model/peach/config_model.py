# model/peach/config_model.py
"""
配置模型 - PDD数据库
"""
from sqlalchemy import Column, String, Text
from app.app import db
from model.common.my_model import MyModel


class Config(db.Model, MyModel):
    __tablename__ = "config"
    __bind_key__ = "pdd"  # 使用pdd数据库绑定

    key = Column(String(100), nullable=False, comment="配置键")
    value = Column(Text, nullable=True, comment="配置值")
    description = Column(String(200), nullable=True, comment="描述")


