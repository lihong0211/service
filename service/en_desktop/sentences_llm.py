# service/en_desktop/sentences_llm.py
"""
调用 DashScope（阿里百炼）OpenAI 兼容接口，给新增单词的一条释义生成英文例句+中文翻译。
只负责拿到 LLM 的原始结果，不做校验——校验交给 service/en_desktop/sentence_quality.py。

跟 service/en_desktop/phonics_llm.py 是同一套调用/重试模式：请求 -> 抽取JSON -> 校验 ->
校验不过把具体错误喂回去重试，最多几次，全部失败返回 None（调用方按 None 静默跳过）。
"""
import json
import os
import re

import requests

from service.en_desktop.sentence_quality import diagnose_sentence

DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_MODEL = "qwen-max"

MAX_SENTENCE_ATTEMPTS = 3

_PROMPT_TEMPLATE = """你是英语词典例句撰写专家，参考真实语料的自然程度写例句，不要写教科书腔调的生硬句子。

单词：{word}
词性：{type}
释义：{content}

要求：
1. 写一句自然、地道的英文例句，准确体现上面这条释义（不是这个单词的其他义项）
2. 句子里必须出现目标单词 "{word}" 本身，或其常见词形变化（时态/单复数/比较级等）
3. 长度适中（约8~20个单词）
4. 开头方式自然多样，不要总是 "The X is..." 或 "A X..." 这类模板句，像正常人组织语言一样
   自然轮换主语类型（人称代词、专有名词、疑问句、祈使句、被动语态等都可以）
5. 附上准确、通顺、符合中文表达习惯的翻译

请把最终答案放进一个 ```json 代码块，格式：
```json
{{"en_text": "...", "zh_text": "..."}}
```
"""

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_sentence(content: str) -> dict | None:
    """从回复里抠出最终 JSON：优先找 ```json 代码块，找不到再退而求其次找最后一对花括号"""
    candidates = list(_JSON_BLOCK_RE.findall(content))
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        candidates.append(content[start : end + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        en_text, zh_text = data.get("en_text"), data.get("zh_text")
        if en_text and zh_text:
            return {"en_text": en_text.strip(), "zh_text": zh_text.strip()}
    return None


def request_example_sentence(
    word: str, meaning_type: str | None, content: str, recent_openers: list[str]
) -> dict | None:
    """
    调用 LLM 返回校验通过的 {"en_text", "zh_text"}；校验用 diagnose_sentence，失败时把
    具体错误原因作为反馈发回去让模型重写，最多尝试 MAX_SENTENCE_ATTEMPTS 次，全部失败返回 None。
    HTTP 失败时直接返回 None（不重试，网络问题跟内容质量是两回事）。
    DASHSCOPE_API_KEY 未配置时直接抛错——这是部署问题，不是单个词的问题，不该被吞掉。
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")

    messages = [
        {
            "role": "user",
            "content": _PROMPT_TEMPLATE.format(word=word, type=meaning_type or "", content=content),
        }
    ]

    for _ in range(MAX_SENTENCE_ATTEMPTS):
        try:
            resp = requests.post(
                DASHSCOPE_CHAT_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": DASHSCOPE_MODEL, "messages": messages, "temperature": 0.7},
                timeout=60,
            )
        except requests.exceptions.RequestException:
            return None
        if resp.status_code != 200:
            return None

        try:
            reply = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None

        sentence = _extract_sentence(reply)
        error = (
            "回复里没有找到合法的 JSON（需要包含 en_text 和 zh_text）"
            if sentence is None
            else diagnose_sentence(word, sentence["en_text"], recent_openers)
        )
        if error is None:
            return sentence

        messages.append({"role": "assistant", "content": reply})
        messages.append(
            {"role": "user", "content": f"校验没通过：{error}。请重新写一句，在新的 ```json 代码块里给出完整答案。"}
        )

    return None
