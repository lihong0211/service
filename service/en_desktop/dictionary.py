# service/en_desktop/dictionary.py
"""
查词：Free Dictionary API 拿词性/释义/音标结构，释义文本再调有道翻译成中文
"""
import requests

from service.en_desktop.youdao import translate_to_chinese

FREE_DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

POS_ABBR = {
    "noun": "n.",
    "verb": "v.",
    "adjective": "adj.",
    "adverb": "adv.",
    "pronoun": "pron.",
    "preposition": "prep.",
    "conjunction": "conj.",
    "interjection": "interj.",
    "exclamation": "interj.",
    "numeral": "num.",
    "article": "art.",
}


def _pick_pronunciation(phonetics: list, tag: str) -> str:
    for p in phonetics:
        if tag in (p.get("audio") or "") and p.get("text"):
            return p.get("text", "")
    return ""


def _any_pronunciation(phonetics: list) -> str:
    for p in phonetics:
        if p.get("text"):
            return p.get("text", "")
    return ""


def lookup_word(word: str) -> dict | None:
    """
    返回结构：{"word", "meaning": [{"type", "content"}], "en_pronunciation", "us_pronunciation"}
    查不到时返回 None
    """
    resp = requests.get(FREE_DICTIONARY_API_URL.format(word=word), timeout=5)
    if resp.status_code != 200:
        return None

    entries = resp.json()
    if not entries:
        return None

    entry = entries[0]
    phonetics = entry.get("phonetics", [])
    # 兜底顺序：uk标注 -> us标注 -> 词条级 phonetic -> 随便一个有文本的音标 -> 占位符
    fallback = entry.get("phonetic") or _any_pronunciation(phonetics) or "-"

    en_pronunciation = _pick_pronunciation(phonetics, "-uk") or fallback
    us_pronunciation = _pick_pronunciation(phonetics, "-us") or fallback

    meaning = []
    for m in entry.get("meanings", []):
        definitions = m.get("definitions") or []
        if not definitions:
            continue
        definition_text = definitions[0].get("definition", "")
        if not definition_text:
            continue

        pos = POS_ABBR.get(m.get("partOfSpeech", ""), m.get("partOfSpeech", ""))
        content = translate_to_chinese(definition_text) or definition_text
        meaning.append({"type": pos, "content": content})

    if not meaning:
        return None

    return {
        "word": word,
        "meaning": meaning,
        "en_pronunciation": en_pronunciation,
        "us_pronunciation": us_pronunciation,
    }
