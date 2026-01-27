# model/peach/ali_report.py
"""
阿里报告检查模型 - PDD数据库
"""
from sqlalchemy import Column, String, Text, Integer, Float
from app.app import db
from model.common.base_model import BaseModel


class AliRpCheck(db.Model, BaseModel):
    __tablename__ = "ali_rp_check"
    __bind_key__ = "pdd"  # 使用pdd数据库绑定
    deleted_at_value = False  # 禁用 deleted_at 过滤

    pharmacist = Column(String(100), nullable=True, comment="药师")
    patientSex = Column(String(10), nullable=True, comment="患者性别")
    patientAge = Column(String(20), nullable=True, comment="患者年龄")
    primaryDiagnosis = Column(String(200), nullable=True, comment="主要诊断")
    medicines = Column(Text, nullable=True, comment="药品")
    pass_flag = Column(
        "pass", Integer(), nullable=True, comment="是否通过"
    )  # 数据库字段名为pass
    reason = Column(Text, nullable=True, comment="原因")
    query = Column(Text, nullable=True, comment="查询")
    rpID = Column(String(100), nullable=True, comment="处方ID")
    refuse = Column(Integer(), default=0, comment="拒绝次数")
    costTime = Column(Float, nullable=True, comment="耗时")
