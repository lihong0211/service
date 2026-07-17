# model/en_desktop/users.py
"""
en-desktop 用户模型（english_new.users）
"""
from sqlalchemy import Column, DateTime, Integer, String

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopUser(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "users"

    username = Column(String(20), unique=True, index=True, nullable=True, comment="账号密码登录用户名")
    password = Column(String(255), nullable=True, comment="bcrypt 哈希")
    wx = Column(String(64), unique=True, index=True, nullable=True, comment="微信 openid")
    nickname = Column(String(50), nullable=True)
    avatar = Column(String(255), nullable=True)
    phone = Column(String(11), index=True, nullable=True)
    description = Column(String(255), nullable=True)
    active = Column(Integer, default=1, comment="1激活 0禁用")
    token = Column(String(64), unique=True, index=True, nullable=True, comment="登录令牌，单设备在线")
    token_expires_at = Column(DateTime(), nullable=True)

    def public_dict(self) -> dict:
        """对外输出，绝不包含 password/token"""
        return {
            "id": self.id,
            "username": self.username,
            "wx": self.wx,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "phone": self.phone,
            "description": self.description,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
