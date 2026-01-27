# model/peach/check_report_model.py
"""
检查报告模型 - PDD数据库
"""
from sqlalchemy import Column, String, Text, Integer
from app.app import db
from model.common.my_model import MyModel


class CheckReport(db.Model, MyModel):
    __tablename__ = "check_report"
    __bind_key__ = "pdd"  # 使用pdd数据库绑定

    platform = Column(String(50), nullable=True, comment="平台")
    patientSex = Column(String(10), nullable=True, comment="患者性别")
    patientAge = Column(String(20), nullable=True, comment="患者年龄")
    primaryDiagnosis = Column(String(200), nullable=True, comment="主要诊断")
    medicines = Column(Text, nullable=True, comment="药品")
    pass_flag = Column(Integer(), nullable=True, comment="是否通过")
    params = Column(Text, nullable=True, comment="参数")
    error = Column(Text, nullable=True, comment="错误")
    isNotMatch = Column(Integer(), nullable=True, comment="是否不匹配")
    doctor = Column(String(100), nullable=True, comment="医生")
    medicineName = Column(String(200), nullable=True, comment="药品名称")
    specification = Column(String(200), nullable=True, comment="规格")
    takeDirection = Column(String(200), nullable=True, comment="给药途径")
    takeFrequence = Column(String(200), nullable=True, comment="给药频率")
    medicineAmount = Column(String(100), nullable=True, comment="药品数量")
    takeDose = Column(String(200), nullable=True, comment="给药剂量")
    formType = Column(String(100), nullable=True, comment="剂型")


