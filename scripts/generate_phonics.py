#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为 words 表里还没有拼读拆分数据的单词生成 word_phonics 记录。

用法：
    .venv/bin/python scripts/generate_phonics.py                     # dry-run，处理全部缺失的词
    .venv/bin/python scripts/generate_phonics.py --limit 50          # dry-run，只处理前 50 个（小样本试跑）
    .venv/bin/python scripts/generate_phonics.py --limit 50 --apply  # 真正写库

--dry-run 是默认行为（不加 --apply 就是 dry-run），跟 rebuild_roots_affixes.py 的约定一致。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, set_request_session  # noqa: E402
from model.en_desktop import EnDesktopWord, EnDesktopWordPhonics  # noqa: E402
from service.en_desktop.phonics import validate_segments  # noqa: E402
from service.en_desktop.phonics_llm import request_phonics_segments  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=None, help="只处理前 N 个缺失拼读数据的词，用于小样本试跑"
    )
    parser.add_argument("--apply", action="store_true", help="真正写库，不加则只是 dry-run")
    args = parser.parse_args()

    session = SessionLocal()
    set_request_session(session)

    existing_word_ids = {p.word_id for p in session.query(EnDesktopWordPhonics).all()}
    query = (
        session.query(EnDesktopWord)
        .where(EnDesktopWord.deleted_at.is_(None))
        .order_by(EnDesktopWord.id.asc())
    )
    # 缺失拼读数据的词可能不连续，多取一批候选再在 Python 侧过滤够 --limit 个
    candidates = query.limit(args.limit * 5 + 50).all() if args.limit else query.all()
    todo = [w for w in candidates if w.id not in existing_word_ids]
    if args.limit:
        todo = todo[: args.limit]

    stats = {"success": 0, "skipped": 0, "failed": 0}
    for w in todo:
        ipa = w.us_pronunciation or w.en_pronunciation
        if not ipa:
            print(f"跳过 {w.word}（无音标）")
            stats["skipped"] += 1
            continue

        segments = request_phonics_segments(w.word, ipa)
        if segments is None:
            print(f"跳过 {w.word}：LLM 调用失败或返回格式不对")
            stats["failed"] += 1
            continue

        if not validate_segments(w.word, ipa, segments):
            print(f"跳过 {w.word}：拆分校验不通过，LLM 返回 {segments}")
            stats["failed"] += 1
            continue

        tag = "[APPLY]" if args.apply else "[DRY-RUN]"
        print(f"{tag} {w.word} {ipa} -> {segments}")
        if args.apply:
            session.add(EnDesktopWordPhonics(word_id=w.id, segments=segments))
        stats["success"] += 1

    if args.apply:
        session.commit()

    print(
        f"\n完成：成功 {stats['success']}，跳过(无音标) {stats['skipped']}，"
        f"失败(校验/接口) {stats['failed']}"
    )


if __name__ == "__main__":
    main()
