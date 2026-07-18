# model/en_desktop/roots.py
"""
en-desktop 词根模型（english_new.roots）
合并存储的多变体条目已拆分为独立行，例词关联 words 表（见 root_words）；
旧的 similar / cases 两列已随这次重建一起删除。
"""
from sqlalchemy import Column, ForeignKey, Integer, String

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopRoot(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "roots"

    name = Column(String(255), nullable=False, comment="词根名称")
    meaning = Column(String(255), nullable=True, comment="含义")

    def to_dict(self, words: list | None = None) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "meaning": self.meaning,
            "words": words if words is not None else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EnDesktopRootWord(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "root_words"

    root_id = Column(Integer, ForeignKey("roots.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False)
