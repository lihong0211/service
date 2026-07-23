# model/en_desktop/word_sentences.py
"""
en-desktop 单词例句模型（english_new.word_sentences）
"""
from sqlalchemy import Column, ForeignKey, Integer, String

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopWordSentence(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "word_sentences"

    word_meaning_id = Column(
        Integer,
        ForeignKey("word_meanings.id", ondelete="CASCADE"),
        nullable=False,
        comment="词性/释义ID，一个词性对应一条例句",
    )
    en_text = Column(String(255), nullable=False, comment="例句原文")
    zh_text = Column(String(255), nullable=False, comment="例句中文翻译")
    audio_url = Column(String(255), nullable=True, comment="例句发音音频地址")
