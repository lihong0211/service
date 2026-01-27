# model/peach/version_model.py
"""
版本模型 - PDD数据库
"""
from sqlalchemy import Column, String, UniqueConstraint
from app.app import db
from model.common.my_model import MyModel


class Version(db.Model, MyModel):
    __tablename__ = "version"
    __bind_key__ = "pdd"  # 使用pdd数据库绑定
    __table_args__ = (
        UniqueConstraint("name", "platform", name="uk_name_platform"),
    )

    version = Column(String(50), nullable=False, comment="版本号")
    name = Column(String(100), nullable=False, comment="名称")
    platform = Column(String(50), nullable=False, comment="平台")


