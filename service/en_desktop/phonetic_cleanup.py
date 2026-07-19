# service/en_desktop/phonetic_cleanup.py
"""
音标遗留符号清理：words 表里的音标是 ECDICT 老式 ASCII 音标（历史字体/编码问题
留下的替代字符，不是标准 Unicode IPA），供 scripts/normalize_phonetics.py 做全库清理用。

已知替代字符（全库统计验证过）：
- ә（西里尔字母 schwa，U+04D9）代替 IPA schwa ə（U+0259）
- є（西里尔字母，U+0454）/ ε（希腊字母 epsilon，U+03B5）代替 IPA ɛ（U+025B）
- ^ 代替浊软腭塞音 ɡ
- 直引号 ' 代替主重音符 ˈ
- ASCII 冒号 : 代替长音符 ː
- (r) 这类圆括号表示可选音，这里统一当作"发这个音"处理，只去括号保留内容

逗号/分号分隔的多音变体、反斜杠损坏的片段、空值/占位符，这些没法靠字符映射修，
交给 needs_refetch 判断，由调用方重新查词典或用 AI 补。
"""
LEGACY_CHAR_MAP = {
    "ә": "ə",
    "є": "ɛ",
    "ε": "ɛ",
    "^": "ɡ",
    "'": "ˈ",
    ":": "ː",
}

# 映射修复后，一个"干净"的音标里应该只包含这些字符
_CLEAN_IPA_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "
    "ˈˌːʃʒŋθðæɒʌɑɔɪʊəɜɚɝɡɛ.'-"
)


def remap_legacy_symbols(raw: str) -> str:
    """
    去掉外层 [...] 包裹、去掉表示可选音的圆括号（保留括号里的内容），
    把已知的历史替代字符换成标准 Unicode IPA 字符。
    不处理逗号/分号/反斜杠这些结构性问题——调用前应该先用 needs_refetch 排除掉。
    """
    body = (raw or "").strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1]
    body = body.replace("(", "").replace(")", "")
    return "".join(LEGACY_CHAR_MAP.get(ch, ch) for ch in body)


def needs_refetch(raw: str | None) -> bool:
    """
    判断这条音标是否坏到没法靠字符映射修，需要重新查词典/让 AI 补：
    - 空值或占位符 "-"
    - 含逗号/分号（多音变体分隔，语义不明确，不猜）
    - 含反斜杠（编码损坏，不可逆）
    - 映射后仍有清单外字符
    """
    if not raw or raw == "-":
        return True
    if "," in raw or ";" in raw or "\\" in raw:
        return True
    remapped = remap_legacy_symbols(raw)
    return any(ch not in _CLEAN_IPA_CHARS for ch in remapped)
