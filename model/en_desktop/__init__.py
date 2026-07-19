# model/en_desktop/__init__.py
"""
en-desktop 模型模块（记单词桌面客户端，english_new 库）
"""
from .affixes import EnDesktopAffix, EnDesktopAffixWord
from .base import BaseEnDesktop
from .daily_expressions import EnDesktopDailyExpression
from .roots import EnDesktopRoot, EnDesktopRootWord
from .users import EnDesktopUser
from .word_libraries import (
    EnDesktopWordLibrary,
    EnDesktopWordLibraryFavorite,
    EnDesktopWordLibraryItem,
)
from .word_meanings import EnDesktopWordMeaning
from .word_phonics import EnDesktopWordPhonics
from .word_sentences import EnDesktopWordSentence
from .words import EnDesktopWord

__all__ = [
    "BaseEnDesktop",
    "EnDesktopUser",
    "EnDesktopWord",
    "EnDesktopWordMeaning",
    "EnDesktopWordPhonics",
    "EnDesktopWordSentence",
    "EnDesktopWordLibrary",
    "EnDesktopWordLibraryItem",
    "EnDesktopWordLibraryFavorite",
    "EnDesktopDailyExpression",
    "EnDesktopRoot",
    "EnDesktopRootWord",
    "EnDesktopAffix",
    "EnDesktopAffixWord",
]
