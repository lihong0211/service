# tests/en_desktop/test_phonics.py
"""
拼读拆分：IPA 分词与校验逻辑测试（纯函数，不依赖数据库）
"""
from service.en_desktop.phonics import (
    diagnose_segments,
    normalize_ipa,
    tokenize_ipa,
    validate_segments,
)


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


def test_tokenize_ipa_handles_reduced_final_i_vowel():
    """有道音标用裸 i（无长音符）表示弱读结尾元音，比如 happy/accuracy 结尾的 i，
    跟长元音 iː、短元音 ɪ 都不是一回事，必须单独收进音素清单"""
    assert tokenize_ipa("/əˈkædəmi/") == ["ə", "k", "æ", "d", "ə", "m", "i"]
    assert tokenize_ipa("/ˈæktʃuəli/") == ["æ", "k", "tʃ", "u", "ə", "l", "i"]


def test_tokenize_ipa_handles_ipa_script_g():
    """有道音标用标准 IPA 的 script g（U+0261 ɡ），不是 ASCII 字母 g（U+0067）"""
    assert tokenize_ipa("/əˈɡen/") == ["ə", "ɡ", "e", "n"]


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


def test_diagnose_segments_valid_returns_none():
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "a", "ipa": "æ"}, {"letters": "t", "ipa": "t"}]
    assert diagnose_segments("cat", "/kæt/", segments) is None


def test_diagnose_segments_empty_list():
    assert diagnose_segments("cat", "/kæt/", []) == "没有返回任何 segments"


def test_diagnose_segments_letters_mismatch_names_actual_and_expected():
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "o", "ipa": "æ"}, {"letters": "t", "ipa": "t"}]
    msg = diagnose_segments("cat", "/kæt/", segments)
    assert "cot" in msg
    assert "cat" in msg


def test_diagnose_segments_ipa_mismatch_names_actual_and_expected():
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "a", "ipa": "e"}, {"letters": "t", "ipa": "t"}]
    msg = diagnose_segments("cat", "/kæt/", segments)
    assert "ket" in msg
    assert "kæt" in msg


def test_diagnose_segments_unknown_ipa_symbol_names_the_segment():
    segments = [{"letters": "ca", "ipa": "k@"}, {"letters": "t", "ipa": "t"}]
    msg = diagnose_segments("cat", "/k@t/", segments)
    assert "k@" in msg
