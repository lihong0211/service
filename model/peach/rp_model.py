# model/peach/rp_model.py
"""
处方记录模型 - PDD数据库
"""
from sqlalchemy import Column, String, Text, DateTime
from app.app import db
from model.common.my_model import MyModel


class Rp(db.Model, MyModel):
    __tablename__ = "rp"
    __bind_key__ = "pdd"  # 使用pdd数据库绑定

    sessionid = Column(String(100), nullable=True, comment="会话ID")
    name = Column(String(100), nullable=True, comment="姓名")
    age = Column(String(20), nullable=True, comment="年龄")
    sex = Column(String(10), nullable=True, comment="性别")
    pddDiagnosis = Column(String(200), nullable=True, comment="拼多多诊断")
    recommendDiagnosis = Column(String(200), nullable=True, comment="推荐诊断")
    medicine = Column(Text, nullable=True, comment="药品")
    dosage = Column(String(200), nullable=True, comment="剂量")
    time = Column(DateTime, nullable=True, comment="时间")


