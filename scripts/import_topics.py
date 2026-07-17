#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导入主题公共词库（体育、厨房、旅游……）。

词表在 scripts/data/topic_words.json（自编，可随时增删主题/单词），
音标和中文释义从 ECDICT CSV 补全，词库挂系统账号、is_public=1。
幂等：重复执行只补缺；ECDICT 里查不到的词跳过并在结尾报告。

用法：
    .venv/bin/python scripts/import_topics.py            # 需要 scripts/ecdict.csv（没有会自动下载）
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from import_ecdict import (  # noqa: E402
    CSV_FIELD_LIMIT,
    download_csv,
    ensure_library,
    ensure_system_user,
    parse_meanings,
)

from app.database import SessionLocal, set_request_session  # noqa: E402
from model.en_desktop import (  # noqa: E402
    EnDesktopWord,
    EnDesktopWordLibraryItem,
    EnDesktopWordMeaning,
)

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
TOPIC_JSON = os.path.join(SCRIPTS_DIR, "data", "topic_words.json")
ECDICT_CSV = os.path.join(SCRIPTS_DIR, "ecdict.csv")


def build_ecdict_index(csv_path: str, needed: set) -> dict:
    """word(小写) -> (phonetic, translation)，只保留主题词表用得到的行"""
    csv.field_size_limit(CSV_FIELD_LIMIT)
    index = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row.get("word") or "").strip().lower()
            if key in needed and key not in index:
                index[key] = (
                    (row.get("phonetic") or "").strip(),
                    row.get("translation") or "",
                )
    return index


def main():
    with open(TOPIC_JSON, encoding="utf-8") as f:
        topics = json.load(f)

    if not os.path.exists(ECDICT_CSV):
        download_csv(ECDICT_CSV)

    needed = {w.strip().lower() for words in topics.values() for w in words}
    ecdict = build_ecdict_index(ECDICT_CSV, needed)

    session = SessionLocal()
    set_request_session(session)

    system_user_id = ensure_system_user(session)
    lib_ids = {name: ensure_library(session, system_user_id, name, category="主题词库") for name in topics}
    session.commit()

    word_ids = {w.word.lower(): w.id for w in session.query(EnDesktopWord).all()}
    existing_items = {
        (item.word_library_id, item.word_id): item
        for item in session.query(EnDesktopWordLibraryItem).all()
    }

    stats = {"new_words": 0, "new_items": 0, "restored_items": 0}
    missing = []

    for topic, words in topics.items():
        lib_id = lib_ids[topic]
        for raw in words:
            key = raw.strip().lower()
            word_id = word_ids.get(key)

            if word_id is None:
                if key not in ecdict:
                    missing.append((topic, raw))
                    continue
                phonetic, translation = ecdict[key]
                meanings = parse_meanings(translation)
                if not meanings:
                    missing.append((topic, raw))
                    continue
                phonetic = f"[{phonetic}]"[:64] if phonetic else None
                w = EnDesktopWord(word=key, en_pronunciation=phonetic, us_pronunciation=phonetic)
                session.add(w)
                session.flush()
                word_id = w.id
                word_ids[key] = word_id
                for m in meanings:
                    session.add(
                        EnDesktopWordMeaning(word_id=word_id, type=m["type"], content=m["content"])
                    )
                stats["new_words"] += 1

            item_key = (lib_id, word_id)
            item = existing_items.get(item_key)
            if item is None:
                item = EnDesktopWordLibraryItem(word_library_id=lib_id, word_id=word_id)
                session.add(item)
                existing_items[item_key] = item
                stats["new_items"] += 1
            elif item.deleted_at is not None:
                item.deleted_at = None
                stats["restored_items"] += 1

        session.commit()

    print("导入完成：")
    print(
        f"  主题词库 {len(topics)} 个，新增单词 {stats['new_words']}，"
        f"新增条目 {stats['new_items']}，恢复条目 {stats['restored_items']}"
    )
    if missing:
        print(f"  ECDICT 未收录（已跳过）{len(missing)} 个：")
        for topic, word in missing:
            print(f"    [{topic}] {word}")


if __name__ == "__main__":
    main()
