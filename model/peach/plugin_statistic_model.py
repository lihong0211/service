# model/peach/plugin_statistic_model.py
"""
插件统计模型 - PDD数据库
"""
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.mysql import TIME
from app.app import db
from model.common.my_model import MyModel


class PluginStatistic(db.Model, MyModel):
    __tablename__ = "plugin_statistic"
    __bind_key__ = "pdd"  # 使用pdd数据库绑定

    user_name = Column(String(100), nullable=False, comment="用户名")
    platform = Column(String(50), nullable=False, comment="平台")
    plugin_version = Column(String(50), nullable=True, comment="插件版本")
    login_time = Column(DateTime, nullable=True, comment="登录时间")
    logout_time = Column(DateTime, nullable=True, comment="登出时间")
    status = Column(String(20), nullable=True, comment="状态")
    duration = Column(Integer, nullable=True, comment="持续时间（秒）")


