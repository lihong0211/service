# model/en_desktop/word_libraries.py
"""
en-desktop 词库模型（english_new.word_libraries / word_library_items，歌单式）
"""
from sqlalchemy import Column, ForeignKey, Integer, String

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopWordLibrary(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "word_libraries"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False, comment="词库名称")
    description = Column(String(255), nullable=True)
    is_public = Column(Integer, default=0, comment="1公开 0私有")

    def to_dict(self, word_count: int = 0) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_public": self.is_public,
            "word_count": word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EnDesktopWordLibraryItem(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "word_library_items"

    word_library_id = Column(
        Integer, ForeignKey("word_libraries.id", ondelete="CASCADE"), nullable=False
    )
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False)


class EnDesktopWordLibraryFavorite(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "word_library_favorites"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_library_id = Column(
        Integer, ForeignKey("word_libraries.id", ondelete="CASCADE"), nullable=False
    )
