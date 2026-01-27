# model/peach/manual_model.py
"""
手动记录模型 - PDD数据库
"""
from sqlalchemy import Column, String, Text, DateTime
from app.app import db
from model.common.my_model import MyModel


class Manual(db.Model, MyModel):
    __tablename__ = "manual"
    __bind_key__ = "pdd"  # 使用pdd数据库绑定

    sessionid = Column(String(100), nullable=True, comment="会话ID")
    type = Column(String(50), nullable=True, comment="类型")
    time = Column(DateTime, nullable=True, comment="时间")
    session_data = Column(Text, nullable=True, comment="会话数据")


