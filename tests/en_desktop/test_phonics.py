# tests/en_desktop/test_phonics.py
"""
拼读拆分：IPA 分词与校验逻辑测试（纯函数，不依赖数据库）
"""
from service.en_desktop.phonics import normalize_ipa, tokenize_ipa, validate_segments


def test_normalize_ipa_strips_slashes_stress_and_dots():
    assert normalize_ipa("/ˈæp.əl/") == "æpəl"


def test_normalize_ipa_strips_brackets():
    assert normalize_ipa("[ˈæpəl]") == "æpəl"


def test_tokenize_ipa_regular_word():
    assert tokenize_ipa("/kæt/") == ["k", "æ", "t"]


def test_tokenize_ipa_handles_affricate_and_diphthong():
    assert tokenize_ipa("/tʃeɪr/") == ["tʃ", "eɪ", "r"]


def test_tokenize_ipa_unknown_symbol_returns_none():
    assert tokenize_ipa("/k@t/") is None


def test_validate_segments_valid():
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "a", "ipa": "æ"}, {"letters": "t", "ipa": "t"}]
    assert validate_segments("cat", "/kæt/", segments) is True


def test_validate_segments_letters_mismatch():
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "o", "ipa": "æ"}, {"letters": "t", "ipa": "t"}]
    assert validate_segments("cat", "/kæt/", segments) is False


def test_validate_segments_ipa_mismatch():
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "a", "ipa": "e"}, {"letters": "t", "ipa": "t"}]
    assert validate_segments("cat", "/kæt/", segments) is False


def test_validate_segments_rejects_unknown_ipa_symbol():
    segments = [{"letters": "ca", "ipa": "k@"}, {"letters": "t", "ipa": "t"}]
    assert validate_segments("cat", "/k@t/", segments) is False


def test_validate_segments_empty_list_is_invalid():
    assert validate_segments("cat", "/kæt/", []) is False
