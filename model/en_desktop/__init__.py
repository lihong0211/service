# model/en_desktop/__init__.py
"""
en-desktop 模型模块（记单词桌面客户端，english_new 库）
"""
from .base import BaseEnDesktop
from .users import EnDesktopUser
from .word_libraries import (
    EnDesktopWordLibrary,
    EnDesktopWordLibraryFavorite,
    EnDesktopWordLibraryItem,
)
from .word_meanings import EnDesktopWordMeaning
from .words import EnDesktopWord

__all__ = [
    "BaseEnDesktop",
    "EnDesktopUser",
    "EnDesktopWord",
    "EnDesktopWordMeaning",
    "EnDesktopWordLibrary",
    "EnDesktopWordLibraryItem",
    "EnDesktopWordLibraryFavorite",
]
