# tests/en_desktop/test_phonics.py
"""
拼读拆分：IPA 分词与校验逻辑测试（纯函数，不依赖数据库）
"""
from service.en_desktop.phonics import normalize_ipa, tokenize_ipa


def test_normalize_ipa_strips_slashes_stress_and_dots():
    assert normalize_ipa("/ˈæp.əl/") == "æpəl"


def test_tokenize_ipa_regular_word():
    assert tokenize_ipa("/kæt/") == ["k", "æ", "t"]


def test_tokenize_ipa_handles_affricate_and_diphthong():
    assert tokenize_ipa("/tʃeɪr/") == ["tʃ", "eɪ", "r"]


def test_tokenize_ipa_unknown_symbol_returns_none():
    assert tokenize_ipa("/k@t/") is None
