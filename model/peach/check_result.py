# model/peach/check_result.py
"""
检查报告模型 - PDD数据库
"""
from sqlalchemy import Column, String, Text, Integer
from app.app import db
from model.common.base_model import BaseModel


class CheckResult(db.Model, BaseModel):
    __tablename__ = "check_result"
    __bind_key__ = "pdd"  # 使用pdd数据库绑定
    deleted_at_value = False  # 禁用 deleted_at 过滤

    platform = Column(String(50), nullable=True, comment="平台")
    patientSex = Column(String(10), nullable=True, comment="患者性别")
    patientAge = Column(String(20), nullable=True, comment="患者年龄")
    primaryDiagnosis = Column(String(200), nullable=True, comment="主要诊断")
    medicines = Column(Text, nullable=True, comment="药品")
    pass_flag = Column(
        "pass", Integer(), nullable=True, comment="是否通过"
    )  # 数据库字段名为pass，属性名为pass_flag
    params = Column(Text, nullable=True, comment="参数")
    error = Column(Text, nullable=True, comment="错误")
    isNotMatch = Column(Integer(), nullable=True, comment="是否不匹配")
    medicineName = Column(String(200), nullable=True, comment="药品名称")
    specification = Column(String(200), nullable=True, comment="规格")
    takeDirection = Column(String(200), nullable=True, comment="给药途径")
    takeFrequence = Column(String(200), nullable=True, comment="给药频率")
    medicineAmount = Column(String(100), nullable=True, comment="药品数量")
    takeDose = Column(String(200), nullable=True, comment="给药剂量")
    formType = Column(String(100), nullable=True, comment="剂型")
