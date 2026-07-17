# model/en_desktop/base.py
"""
en-desktop 模块基础模型。

用独立的 declarative_base：english 模块已在共享 Base 上注册了同名的 words 表
（结构不同、库不同），同一份 MetaData 不允许重复注册表名。
所有模型挂 __bind_key__ = "en_desktop"，由 _RoutingSession 路由到 english_new 库。

字段名沿用 english_new 库现有表结构（created_at/updated_at，区别于
model/common/base_model.py 的 create_at/update_at），CRUD 方法只保留本模块用到的子集。
"""
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import declarative_base

from app.database import db

BaseEnDesktop = declarative_base()


def get_datetime_now():
    return datetime.now()


class EnDesktopModel:
    """en-desktop 基础模型：软删除 + 等值条件查询的通用 CRUD"""

    __bind_key__ = "en_desktop"

    id = Column(INTEGER(11), primary_key=True)
    created_at = Column(DateTime(), default=get_datetime_now, comment="创建时间")
    updated_at = Column(
        DateTime(), default=get_datetime_now, onupdate=get_datetime_now, comment="修改时间"
    )
    deleted_at = Column(DateTime(), nullable=True, comment="删除时间")

    @classmethod
    def loads(cls, json_data):
        item = cls()
        for key, value in json_data.items():
            if hasattr(cls, key) and value is not None:
                setattr(item, key, value)
        return item

    @classmethod
    def insert(cls, json_data, commit=True):
        item = cls.loads(json_data)
        db.session.add(item)
        db.session.flush()
        if commit:
            db.session.commit()
        return item.id

    @classmethod
    def update(cls, json_data, commit=True):
        update_cols = {}
        for key, value in json_data.items():
            if (
                hasattr(cls, key)
                and value is not None
                and key not in ["id", "created_at", "updated_at", "deleted_at"]
            ):
                update_cols[key] = value
        db.session.query(cls).where(cls.id == json_data["id"]).update(update_cols)
        if commit:
            db.session.commit()
        return json_data["id"]

    @classmethod
    def delete(cls, primary_key, commit=True):
        """软删除"""
        db.session.query(cls).where(cls.id == primary_key).update(
            {cls.deleted_at: datetime.now()}
        )
        if commit:
            db.session.commit()

    @classmethod
    def delete_by(cls, criterion, commit=True):
        """按条件软删除"""
        cls.builder_query(criterion).update({cls.deleted_at: datetime.now()})
        if commit:
            db.session.commit()

    @classmethod
    def get_by_id(cls, primary_key):
        return (
            db.session.query(cls)
            .where(cls.id == primary_key, cls.deleted_at.is_(None))
            .first()
        )

    @classmethod
    def select_by(cls, criterion=None):
        return cls.builder_query(criterion).all()

    @classmethod
    def select_one_by(cls, criterion):
        return cls.builder_query(criterion).first()

    @classmethod
    def builder_query(cls, criterion=None):
        """等值条件查询，自动过滤软删除记录"""
        query = db.session.query(cls)
        for key, val in (criterion or {}).items():
            if val is not None:
                query = query.where(getattr(cls, key) == val)
        return query.where(cls.deleted_at.is_(None))
