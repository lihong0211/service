# tests/en_desktop/test_phonetic_cleanup.py
"""
音标遗留符号清理测试：把 ECDICT 老式 ASCII 音标里的历史替代字符
（西里尔字母、ASCII 冒号/直引号等）修复成标准 Unicode IPA 字符。
纯函数，不依赖数据库/网络。
"""
from service.en_desktop.phonetic_cleanup import needs_refetch, remap_legacy_symbols


def test_remap_replaces_cyrillic_schwa():
    assert remap_legacy_symbols("[ә'bændәn]") == "əˈbændən"


def test_remap_replaces_cyrillic_epsilon_lookalike():
    assert remap_legacy_symbols("[єә]") == "ɛə"


def test_remap_replaces_caret_with_g():
    assert remap_legacy_symbols("[^ɔd]") == "ɡɔd"


def test_remap_replaces_colon_with_length_mark():
    assert remap_legacy_symbols("['senti,mi:tә(r)]".replace(",", "")) == "ˈsentɪmiːtər"


def test_remap_strips_optional_parens_keeping_content():
    assert remap_legacy_symbols("['mistә(r)]") == "ˈmɪstər"


def test_remap_fixes_ei_diphthong():
    assert remap_legacy_symbols("[ˈeibl]") == "ˈeɪbl"


def test_remap_fixes_au_diphthong():
    assert remap_legacy_symbols("[ә'baut]") == "əˈbaʊt"


def test_remap_fixes_ai_diphthong():
    assert remap_legacy_symbols("[ә'baid]") == "əˈbaɪd"


def test_remap_fixes_ou_diphthong():
    assert remap_legacy_symbols("[ˈskoul]") == "ˈskoʊl"


def test_remap_keeps_long_i_and_u_untouched():
    assert remap_legacy_symbols("[skuːl]") == "skuːl"
    assert remap_legacy_symbols("[bri:vi]") == "briːvɪ"


def test_remap_bare_i_and_u_become_short_vowels():
    assert remap_legacy_symbols("[bit]") == "bɪt"
    assert remap_legacy_symbols("[buk]") == "bʊk"


def test_needs_refetch_true_for_null_or_placeholder():
    assert needs_refetch(None) is True
    assert needs_refetch("") is True
    assert needs_refetch("-") is True


def test_needs_refetch_true_for_comma_variant_forms():
    assert needs_refetch("[di'rektli, dai'rektli]") is True


def test_needs_refetch_true_for_corrupted_backslashes():
    assert needs_refetch("['kɔnv\\\\:sli]") is True


def test_needs_refetch_false_for_clean_remappable_entry():
    assert needs_refetch("[ә'bændәn]") is False
