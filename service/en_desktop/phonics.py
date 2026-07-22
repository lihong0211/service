# service/en_desktop/phonics.py
"""
拼读拆分：IPA 音素清单、分词、字母-音素对齐结果校验。
供 scripts/generate_phonics.py 校验 LLM 返回结果用。
"""
import re

# 英语 IPA 音素清单（含双元音、塞擦音等多字符符号）。
# 按长度降序排列供最长匹配分词使用——不能按字母表排序，"tʃ" 必须排在 "t" 前面。
PHONEMES = sorted(
    [
        # 塞擦音
        "tʃ", "dʒ",
        # 双元音 / r 化元音（多字符，优先匹配）
        "eɪ", "aɪ", "ɔɪ", "aʊ", "oʊ", "əʊ", "ɪə", "eə", "ʊə",
        "ɑːr", "ɔːr", "ɜːr", "ɪr", "ɛr", "ʊr",
        # 长元音
        "iː", "ɑː", "ɔː", "uː", "ɜː",
        # 单元音（含 i/u 弱读结尾元音，现代音标记法，跟长元音 iː/uː、短元音 ɪ/ʊ 都不同，
        # 比如 happy/accuracy 结尾的 i，actual/influence 里的 u）
        "ɪ", "i", "e", "æ", "ʌ", "ɒ", "ʊ", "u", "ə", "ɝ", "ɚ",
        # 辅音（g 用标准 IPA 的 script g ɡ，U+0261，不是 ASCII 字母 g U+0067——
        # 有道接口返回的音标用的是前者）
        "p", "b", "t", "d", "k", "ɡ", "f", "v", "θ", "ð",
        "s", "z", "ʃ", "ʒ", "h", "m", "n", "ŋ", "l", "r", "j", "w",
    ],
    key=len,
    reverse=True,
)

# 音标里忽略的装饰符号：斜杠、方括号、重音符 ˈˌ、音节分隔点、空格
_STRIP_RE = re.compile(r"[/\[\]ˈˌ.\s]")


def normalize_ipa(ipa: str) -> str:
    """去掉 /.../ 或 [...] 包裹、重音符 ˈˌ、音节分隔点 . 和空格"""
    return _STRIP_RE.sub("", ipa or "")


def tokenize_ipa(ipa: str) -> list[str] | None:
    """按 PHONEMES 最长匹配把 IPA 字符串切成音素列表；遇到清单外的符号返回 None"""
    text = normalize_ipa(ipa)
    tokens = []
    i = 0
    while i < len(text):
        for p in PHONEMES:
            if text.startswith(p, i):
                tokens.append(p)
                i += len(p)
                break
        else:
            return None
    return tokens


def diagnose_segments(word: str, ipa: str, segments: list) -> str | None:
    """
    校验 LLM 返回的拆分结果，返回具体哪里错了（供重试时把错误原因喂回给 LLM）；
    全部满足时返回 None：
    1. 所有 letters 依次拼接（忽略大小写）等于原词
    2. 所有 ipa 依次拼接（去装饰符号后）等于原始音标同样处理后的结果
    3. 每一段 ipa 都能被音素清单完整分词（不含清单外符号）
    """
    if not segments:
        return "没有返回任何 segments"
    try:
        letters_concat = "".join(seg["letters"] for seg in segments)
        ipa_concat = "".join(normalize_ipa(seg["ipa"]) for seg in segments)
    except (KeyError, TypeError):
        return "每个 segment 必须同时有 letters 和 ipa 两个字段"

    expected_word = (word or "").lower()
    if letters_concat.lower() != expected_word:
        return f"所有 letters 依次拼接是 {letters_concat!r}，应该逐字符等于单词 {word!r}"

    expected_ipa = normalize_ipa(ipa)
    if ipa_concat != expected_ipa:
        return f"所有 ipa 依次拼接是 {ipa_concat!r}，应该逐字符等于音标处理后的 {expected_ipa!r}"

    for seg in segments:
        if not tokenize_ipa(seg["ipa"]):
            return f"片段 {seg!r} 的 ipa 不是清单内的合法音素组合"
    return None


def validate_segments(word: str, ipa: str, segments: list) -> bool:
    """校验 LLM 返回的拆分结果是否完全通过，规则见 diagnose_segments"""
    return diagnose_segments(word, ipa, segments) is None
