# model/en_desktop/word_phonics.py
"""
en-desktop 单词拼读拆分模型（english_new.word_phonics）
每个单词最多一条记录（word_id 唯一），segments 是 AI 生成并校验过的字母段-音素对齐结果。
"""
from sqlalchemy import Column, ForeignKey, Integer, JSON

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopWordPhonics(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "word_phonics"

    word_id = Column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    segments = Column(JSON, nullable=False)
