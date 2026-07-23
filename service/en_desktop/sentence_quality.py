# service/en_desktop/sentence_quality.py
"""
新增单词自动例句的质量校验：目标词校验 + 开头词多样性校验。
供 service/en_desktop/sentences_llm.py 的重试循环用，只做纯逻辑判断，不碰网络/数据库。

跟 sentence-generation-project 那套"整批200条统计"的质量门槛不是一回事：这里一次只处理一句，
开头词校验改成从数据库现拉最近 N 条 word_sentences 现算分布，不单独维护计数状态。
"""

# 单一开头词在"最近 N 条 + 候选这一条"里的占比上限，对应人工批量流程里
# "任何单一开头词不超过 6%~8%" 的规则（见 opener-diversity-quality-gate 记忆）
MAX_OPENER_RATIO = 0.08


def _word_root(word: str) -> str:
    """跟例句生成项目里目标词校验脚本同样的词根提取：短词整词匹配，长词去掉最后两个字符，
    容忍规则变位（-s/-ed/-ing 等），不追求完美，允许人工复核误报。"""
    w = word.lower()
    return w[: max(4, len(w) - 2)] if len(w) > 4 else w


def diagnose_sentence(word: str, en_text: str, recent_openers: list[str]) -> str | None:
    """
    校验候选例句，返回具体错误原因（喂给 LLM 重试用）；全部通过返回 None。
    1. 句子里必须出现目标单词的词根（大小写不敏感）
    2. 开头词在"最近 N 条 + 这一条"里的占比不能超过 MAX_OPENER_RATIO
    """
    if not en_text or not en_text.strip():
        return "没有生成有效的例句文本"

    root = _word_root(word)
    if root not in en_text.lower():
        return f'句子里没有出现目标单词 "{word}"（或其常见词形变化），检查是不是写偏题了'

    tokens = en_text.strip().split()
    if not tokens:
        return "没有生成有效的例句文本"

    opener = tokens[0].strip('.,!?"\'').lower()
    if opener and recent_openers:
        count = sum(1 for o in recent_openers if o.lower() == opener) + 1  # +1 把候选句自己算进去
        ratio = count / (len(recent_openers) + 1)
        if ratio > MAX_OPENER_RATIO:
            return (
                f'开头词 "{tokens[0]}" 在最近 {len(recent_openers)} 句例句里已经用得偏多了'
                "，换一种句子开头方式（比如换主语类型、用疑问句/祈使句/被动语态等）"
            )

    return None
