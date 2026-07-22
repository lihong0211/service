# service/en_desktop/phonics_openai.py
"""
调用 OpenAI Chat Completions API 做拼读拆分，接口跟 phonics_llm.py 的 DashScope
版本一致（request_phonics_segments(word, ipa) -> list | None），方便对比效果。
用 response_format=json_schema 结构化输出保证格式合法，不用像 DashScope 那样
自己从文本里抠 JSON；reasoning_effort 控制推理力度，避免不设上限地"一直想"。
"""
import json
import os

import requests

from service.en_desktop.phonics import diagnose_segments

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-5.6"
OPENAI_REASONING_EFFORT = "medium"

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
"""

_SEGMENTS_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "phonics_segments",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "letters": {"type": "string"},
                            "ipa": {"type": "string"},
                        },
                        "required": ["letters", "ipa"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["segments"],
            "additionalProperties": False,
        },
    },
}


def request_phonics_segments(word: str, ipa: str) -> list | None:
    """
    调用 OpenAI 返回校验通过的 segments 列表；校验用 diagnose_segments，失败时把具体
    错误原因喂回去重试，最多 MAX_PHONICS_ATTEMPTS 次，全部失败返回 None。
    HTTP/网络失败时直接返回 None（不重试）。OPENAI_API_KEY 未配置时直接抛错。
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置")

    messages = [{"role": "user", "content": _PROMPT_TEMPLATE.format(word=word, ipa=ipa)}]

    for _ in range(MAX_PHONICS_ATTEMPTS):
        try:
            resp = requests.post(
                OPENAI_CHAT_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": OPENAI_MODEL,
                    "messages": messages,
                    "response_format": _SEGMENTS_SCHEMA,
                    "reasoning_effort": OPENAI_REASONING_EFFORT,
                },
                timeout=90,
            )
        except requests.exceptions.RequestException:
            return None
        if resp.status_code != 200:
            return None

        try:
            content = resp.json()["choices"][0]["message"]["content"]
            segments = json.loads(content)["segments"]
        except (KeyError, IndexError, TypeError, ValueError):
            return None

        error = diagnose_segments(word, ipa, segments)
        if error is None:
            return segments

        messages.append({"role": "assistant", "content": content})
        messages.append(
            {"role": "user", "content": f"校验没通过：{error}。请重新检查每一段，修正后给出完整答案。"}
        )

    return None
