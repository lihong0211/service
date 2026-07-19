# tests/en_desktop/test_word_phonics.py
"""
en-desktop 拼读拆分模型测试
"""
import pytest
from sqlalchemy.exc import IntegrityError

from model.en_desktop import EnDesktopWordPhonics


def test_insert_and_query_word_phonics(en_desktop_db):
    segments = [
        {"letters": "c", "ipa": "k"},
        {"letters": "a", "ipa": "æ"},
        {"letters": "t", "ipa": "t"},
    ]
    en_desktop_db.add(EnDesktopWordPhonics(word_id=1, segments=segments))
    en_desktop_db.commit()

    row = (
        en_desktop_db.query(EnDesktopWordPhonics)
        .where(EnDesktopWordPhonics.word_id == 1)
        .first()
    )
    assert row.segments == segments


def test_word_id_unique_constraint(en_desktop_db):
    en_desktop_db.add(EnDesktopWordPhonics(word_id=1, segments=[{"letters": "a", "ipa": "a"}]))
    en_desktop_db.commit()

    en_desktop_db.add(EnDesktopWordPhonics(word_id=1, segments=[{"letters": "b", "ipa": "b"}]))
    with pytest.raises(IntegrityError):
        en_desktop_db.commit()
