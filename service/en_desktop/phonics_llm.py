# service/en_desktop/phonics_llm.py
"""
调用 DashScope（阿里百炼）OpenAI 兼容接口，让 LLM 给出单词的字母段-音素拆分。
只负责拿到 LLM 的原始 segments，不做校验——校验交给 service/en_desktop/phonics.py 的 validate_segments。
"""
import json
import os
import re

import requests

from service.en_desktop.phonics import diagnose_segments

DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_MODEL = "qwen-max"

# 拼读拆分最多尝试几次（首次 + 带错误反馈的重试），把校验失败的具体原因喂回给模型，
# 比盲目重新问一遍更容易收敛到完全正确的答案。
MAX_PHONICS_ATTEMPTS = 3

_PROMPT_TEMPLATE = """你是英语自然拼读（phonics）教学专家。给定单词和它的 IPA 音标，
把单词拆成若干"字母段-音素"对应的片段，用于教学生逐段拼读。

单词：{word}
音标：{ipa}

要求（非常重要，逐条检查后再输出）：
1. 严格按音标里出现的音素顺序拆分，每个片段对应单词里连续的一个或多个字母
2. 每个音素必须对应真正发出这个音的字母/字母组合，参考常见拼读规则（比如 sh/ch/th/ph 这类
   辅音组合各自发一个音，ai/ee/oa/igh 这类元音组合各自发一个音，结尾不发音的 e 跟前一个音节
   算一段）——不能为了让拼接对得上，就把某个音素硬塞给跟它无关的字母
3. 所有片段的 letters 依次拼接必须逐字符等于单词本身（大小写不敏感），不能多字母也不能少字母
4. 所有片段的 ipa 依次拼接必须逐字符等于给定音标去掉 / ˈ ˌ . 和空格后的结果——每个音素只能出现
   在一个片段里，绝不能把同一个音素在两个相邻片段里各写一次，也不能漏掉音标里的任何音素
5. 音标里的字符要原样使用（比如音标写的是 ɪ 就必须用 ɪ，不能自己换成看起来像的 i；音标写的是
   eɪ 就必须整体用 eɪ，不能拆成 e 和 ɪ 两段）

例子（单词 school，音标 /skuːl/）：
{{"segments": [{{"letters": "sch", "ipa": "sk"}}, {{"letters": "oo", "ipa": "uː"}}, {{"letters": "l", "ipa": "l"}}]}}
校验方法：letters 拼起来 "sch"+"oo"+"l" = "school"，跟单词一致；ipa 拼起来 "sk"+"uː"+"l" = "skuːl"，
跟音标（去掉 / 和重音符后）逐字符一致，没有重复也没有遗漏——你的输出也要满足同样的逐字符一致。

请先逐段写出你的拆分和验证过程（letters 拼起来是什么、ipa 拼起来是什么、是否分别等于单词和
音标），确认无误后，把最终答案放进一个 ```json 代码块，格式：
```json
{{"segments": [{{"letters": "...", "ipa": "..."}}]}}
```
"""

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_segments(content: str) -> list | None:
    """从回复里抠出最终 JSON 的 segments：优先找 ```json 代码块，找不到再退而求其次找最后一对花括号"""
    candidates = [m for m in _JSON_BLOCK_RE.findall(content)]
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        candidates.append(content[start : end + 1])

    for candidate in candidates:
        try:
            segments = json.loads(candidate).get("segments")
        except (ValueError, AttributeError):
            continue
        if segments is not None:
            return segments
    return None


def request_phonics_segments(word: str, ipa: str) -> list | None:
    """
    调用 LLM 返回校验通过的 segments 列表；校验用 diagnose_segments，失败时把具体错误
    原因作为反馈发回去让模型重新改，最多尝试 MAX_PHONICS_ATTEMPTS 次，全部失败返回 None。
    HTTP 失败时直接返回 None（不重试，网络问题跟内容质量是两回事）。
    DASHSCOPE_API_KEY 未配置时直接抛错——这是部署问题，不是单个词的问题，不该被吞掉。
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")

    messages = [{"role": "user", "content": _PROMPT_TEMPLATE.format(word=word, ipa=ipa)}]

    for _ in range(MAX_PHONICS_ATTEMPTS):
        resp = requests.post(
            DASHSCOPE_CHAT_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": DASHSCOPE_MODEL, "messages": messages, "temperature": 0},
            timeout=30,
        )
        if resp.status_code != 200:
            return None

        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None

        segments = _extract_segments(content)
        error = "回复里没有找到合法的 JSON" if segments is None else diagnose_segments(word, ipa, segments)
        if error is None:
            return segments

        messages.append({"role": "assistant", "content": content})
        messages.append(
            {"role": "user", "content": f"校验没通过：{error}。请重新检查每一段，修正后在新的 ```json 代码块里给出完整答案。"}
        )

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
