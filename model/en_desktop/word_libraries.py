# model/en_desktop/word_libraries.py
"""
en-desktop 词库模型（english_new.word_libraries / word_library_items，歌单式）
"""
from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopWordLibrary(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "word_libraries"
    # 同一用户下词库名唯一：应用层"先查后插"不是原子操作，并发的重复创建
    # 请求能双双通过检查，靠这个约束在数据库层兜底（详见 sql/ 迁移文件里的说明）
    __table_args__ = (UniqueConstraint("user_id", "name", name="uk_user_library_name"),)

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
