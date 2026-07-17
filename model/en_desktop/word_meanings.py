# model/en_desktop/word_meanings.py
"""
en-desktop 单词释义模型（english_new.word_meanings）
"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopWordMeaning(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "word_meanings"

    word_id = Column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False, comment="单词ID"
    )
    type = Column(String(20), nullable=False, comment="词性")
    content = Column(Text, nullable=False, comment="释义内容")
