# model/en_desktop/words.py
"""
en-desktop 单词模型（english_new.words，与 english 模块的 words 表不是同一张）
"""
from sqlalchemy import Column, String

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopWord(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "words"

    word = Column(String(30), unique=True, index=True, nullable=False)
    en_pronunciation = Column(String(64), nullable=True)
    us_pronunciation = Column(String(64), nullable=True)

    def to_dict(self, meaning: list | None = None) -> dict:
        return {
            "id": self.id,
            "word": self.word,
            "en_pronunciation": self.en_pronunciation,
            "us_pronunciation": self.us_pronunciation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "meaning": meaning if meaning is not None else [],
        }
