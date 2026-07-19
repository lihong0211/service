#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把 words 表里 ECDICT 老式 ASCII 音标（西里尔字母/ASCII 冒号等历史替代字符）
清理成标准 Unicode IPA。

处理逻辑（en_pronunciation / us_pronunciation 两列各自独立判断）：
1. 能靠字符映射确定性修复的（不含逗号/分号/反斜杠，映射后字符都在白名单内）：
   直接替换成 "[标准 IPA]"，不调用任何外部接口。
2. 修不了的（空值/占位符、含逗号分号的多音变体、反斜杠损坏、映射后仍有异常字符）：
   先查 Free Dictionary API 拿权威音标；查不到再用 LLM 兜底生成，并在日志里
   标注 "[AI 生成，建议复核]"。两种情况都查/生成失败则保留原值不动，记入需人工复核清单。

用法：
    .venv/bin/python scripts/normalize_phonetics.py                  # dry-run，处理全部词
    .venv/bin/python scripts/normalize_phonetics.py --limit 20       # dry-run，兜底桶只试前 20 个
    .venv/bin/python scripts/normalize_phonetics.py --limit 20 --apply  # 真正写库

写库前务必先手动备份 words 表，例如：
    mysqldump -h <host> -u <user> -p english_new words > words_backup_$(date +%Y%m%d).sql
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, set_request_session  # noqa: E402
from model.en_desktop import EnDesktopWord  # noqa: E402
from service.en_desktop.dictionary import fetch_pronunciation  # noqa: E402
from service.en_desktop.phonics_llm import request_ipa_pronunciation  # noqa: E402
from service.en_desktop.phonetic_cleanup import (  # noqa: E402
    needs_refetch,
    remap_legacy_symbols,
)


def _clean_value(raw, refetched):
    """raw 是原始列值；refetched 是这个词查/生成好的兜底结果（可能为 None）。"""
    if not needs_refetch(raw):
        return f"[{remap_legacy_symbols(raw)}]"
    return refetched


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=None, help="兜底桶（需要查词典/AI）只处理前 N 个，用于小样本试跑"
    )
    parser.add_argument("--apply", action="store_true", help="真正写库，不加则只是 dry-run")
    args = parser.parse_args()

    session = SessionLocal()
    set_request_session(session)

    words = (
        session.query(EnDesktopWord)
        .where(EnDesktopWord.deleted_at.is_(None))
        .order_by(EnDesktopWord.id.asc())
        .all()
    )

    stats = {"remapped": 0, "dictionary": 0, "llm": 0, "manual_review": 0}
    manual_review_words = []
    refetch_budget = args.limit

    for w in words:
        needs_word_refetch = needs_refetch(w.en_pronunciation) or needs_refetch(w.us_pronunciation)
        refetched = None

        if needs_word_refetch:
            if refetch_budget is not None and refetch_budget <= 0:
                continue
            fetched = fetch_pronunciation(w.word)
            if fetched:
                refetched = fetched
                stats["dictionary"] += 1
                print(f"[词典] {w.word} -> {fetched}")
            else:
                llm_ipa = request_ipa_pronunciation(w.word)
                if llm_ipa:
                    refetched = {"en_pronunciation": llm_ipa, "us_pronunciation": llm_ipa}
                    stats["llm"] += 1
                    print(f"[AI 生成，建议复核] {w.word} -> {llm_ipa}")
                else:
                    stats["manual_review"] += 1
                    manual_review_words.append(w.word)
                    print(f"[需人工复核] {w.word}：词典查不到，AI 也没生成")
            if refetch_budget is not None:
                refetch_budget -= 1

        new_en = _clean_value(
            w.en_pronunciation, refetched["en_pronunciation"] if refetched else None
        )
        new_us = _clean_value(
            w.us_pronunciation, refetched["us_pronunciation"] if refetched else None
        )

        if not needs_word_refetch:
            stats["remapped"] += 1

        if args.apply:
            if new_en is not None:
                w.en_pronunciation = new_en
            if new_us is not None:
                w.us_pronunciation = new_us

    if args.apply:
        session.commit()

    print(
        f"\n完成：确定性映射 {stats['remapped']}，词典补全 {stats['dictionary']}，"
        f"AI 兜底 {stats['llm']}，需人工复核 {stats['manual_review']}"
    )
    if manual_review_words:
        print("需人工复核的词：" + "、".join(manual_review_words))


if __name__ == "__main__":
    main()
