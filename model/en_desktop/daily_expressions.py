# model/en_desktop/daily_expressions.py
"""
en-desktop 日常用语模型（english_new.daily_expressions）
"""
from sqlalchemy import Column, String

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopDailyExpression(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "daily_expressions"

    phrase = Column(String(1000), nullable=False)
    meaning = Column(String(1000), nullable=False)
    audio_url = Column(String(255), nullable=True, comment="日常表达发音音频地址")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "phrase": self.phrase,
            "meaning": self.meaning,
            "audio_url": self.audio_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
