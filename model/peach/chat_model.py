# model/peach/chat_model.py
"""
聊天记录模型 - PDD数据库
"""
from sqlalchemy import Column, String, Text, DateTime, Float
from app.app import db
from model.common.my_model import MyModel


class Chat(db.Model, MyModel):
    __tablename__ = "chat"
    __bind_key__ = "pdd"  # 使用pdd数据库绑定

    sessionid = Column(String(100), nullable=True, comment="会话ID")
    req_content = Column(Text, nullable=True, comment="请求内容")
    res_content = Column(Text, nullable=True, comment="响应内容")
    cost = Column(Float, nullable=True, comment="成本")
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")


