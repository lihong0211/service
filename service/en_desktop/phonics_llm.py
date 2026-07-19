# service/en_desktop/phonics_llm.py
"""
调用 DashScope（阿里百炼）OpenAI 兼容接口，让 LLM 给出单词的字母段-音素拆分。
只负责拿到 LLM 的原始 segments，不做校验——校验交给 service/en_desktop/phonics.py 的 validate_segments。
"""
import json
import os

import requests

DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_MODEL = "qwen-plus"

_PROMPT_TEMPLATE = """你是英语自然拼读（phonics）教学专家。给定单词和它的 IPA 音标，
把单词拆成若干"字母段-音素"对应的片段，用于教学生逐段拼读。

单词：{word}
音标：{ipa}

要求：
1. 严格按音标里出现的音素顺序拆分，每个片段对应单词里连续的一个或多个字母
2. 所有片段的 letters 依次拼接必须完全等于单词本身（大小写不敏感）
3. 所有片段的 ipa 依次拼接必须完全等于给定音标去掉 / ˈ ˌ . 和空格后的结果
4. 只返回 JSON，不要任何解释文字，格式：{{"segments": [{{"letters": "...", "ipa": "..."}}]}}
"""


def request_phonics_segments(word: str, ipa: str) -> list | None:
    """
    调用 LLM 返回 segments 列表（未校验）。
    HTTP 失败或返回内容解析不出合法 JSON 时返回 None，由调用方决定跳过。
    DASHSCOPE_API_KEY 未配置时直接抛错——这是部署问题，不是单个词的问题，不该被吞掉。
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")

    payload = {
        "model": DASHSCOPE_MODEL,
        "messages": [{"role": "user", "content": _PROMPT_TEMPLATE.format(word=word, ipa=ipa)}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    resp = requests.post(
        DASHSCOPE_CHAT_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        return None

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)["segments"]
    except (KeyError, IndexError, ValueError, TypeError):
        return None


_IPA_PROMPT_TEMPLATE = """你是英语词典编纂专家。给出单词的美式英语 IPA 音标。

单词：{word}

要求：
1. 只返回音标本身，用 /.../ 包裹，标准 Unicode IPA 字符（重音符用 ˈˌ，长音符用 ː）
2. 不要任何解释文字、不要词性、不要例句
"""


def request_ipa_pronunciation(word: str) -> str | None:
    """
    数据库音标坏到没法修、词典 API 也查不到时的最后兜底：让 LLM 直接给出音标。
    调用方应该把这类结果标记为"AI 生成，建议复核"，不当作权威数据源。
    HTTP 失败或返回空内容时返回 None。
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")

    payload = {
        "model": DASHSCOPE_MODEL,
        "messages": [{"role": "user", "content": _IPA_PROMPT_TEMPLATE.format(word=word)}],
        "temperature": 0,
    }
    resp = requests.post(
        DASHSCOPE_CHAT_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        return None

    try:
        content = resp.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        return None
    return content or None
