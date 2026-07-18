# model/en_desktop/affixes.py
"""
en-desktop 词缀模型（english_new.affixes，从旧 english.affix 迁移而来）
例词改成关联 words 表（见 affix_words），旧的 cases 列留在库里不再读写。
"""
from sqlalchemy import Column, ForeignKey, Integer, String

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopAffix(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "affixes"

    name = Column(String(255), nullable=False, comment="词缀名称")
    meaning = Column(String(255), nullable=True, comment="含义")
    similar = Column(String(255), nullable=True, comment="相似词缀，逗号分隔存储")

    def to_dict(self, words: list | None = None) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "meaning": self.meaning,
            "similar": self.similar.split(",") if self.similar else [],
            "words": words if words is not None else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EnDesktopAffixWord(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "affix_words"

    affix_id = Column(Integer, ForeignKey("affixes.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False)
