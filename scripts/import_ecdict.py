#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 ECDICT（MIT，https://github.com/skywind3000/ECDICT）导入系统公共词库。

按考试 tag + COCA 词频切出多个词库，挂在系统账号（username=system）名下，
is_public=1。幂等：重复执行只补缺，不覆盖已有单词的释义。

用法：
    .venv/bin/python scripts/import_ecdict.py            # 自动下载 CSV 到 scripts/ecdict.csv
    .venv/bin/python scripts/import_ecdict.py --csv /path/to/ecdict.csv
"""
import argparse
import csv
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, set_request_session  # noqa: E402
from model.en_desktop import (  # noqa: E402
    EnDesktopUser,
    EnDesktopWord,
    EnDesktopWordLibrary,
    EnDesktopWordLibraryItem,
    EnDesktopWordMeaning,
)

ECDICT_CSV_URL = "https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv"
SYSTEM_USERNAME = "system"

# 词库定义：名称 -> 入选条件（tag 包含 / COCA 词频名次上限）
FREQ_TOP_N = 5000
LIBRARIES = [
    ("中考核心词汇", {"tag": "zk"}),
    ("高考核心词汇", {"tag": "gk"}),
    ("四级核心词汇", {"tag": "cet4"}),
    ("六级核心词汇", {"tag": "cet6"}),
    ("考研核心词汇", {"tag": "ky"}),
    (f"高频核心Top{FREQ_TOP_N}", {"frq_top": FREQ_TOP_N}),
]

WORD_RE = re.compile(r"^[A-Za-z][A-Za-z\-' .]*$")
# 释义行的词性前缀，如 "n."、"vt. & vi."、"adj."
POS_RE = re.compile(r"^((?:[a-z]+\.)(?:\s*&\s*[a-z]+\.)*)\s*(.*)$")

CSV_FIELD_LIMIT = 10 * 1024 * 1024


def download_csv(path: str) -> None:
    print(f"下载 ECDICT CSV -> {path}（约 66MB）...")
    urllib.request.urlretrieve(ECDICT_CSV_URL, path)
    print("下载完成")


def parse_meanings(translation: str) -> list:
    """'n. 苹果\\nvt. 削...' -> [{type, content}]，无词性前缀的行 type 为空串。
    ECDICT 的 translation 用字面量 \\n（反斜杠+n）转义换行，先还原再切分。"""
    meanings = []
    normalized = (translation or "").replace("\\n", "\n")
    for line in normalized.splitlines():
        line = line.strip()
        if not line:
            continue
        m = POS_RE.match(line)
        if m and m.group(2):
            meanings.append({"type": m.group(1)[:20], "content": m.group(2)})
        else:
            meanings.append({"type": "", "content": line})
    return meanings


def wanted_rows(csv_path: str):
    """遍历 CSV，产出 (word, phonetic, meanings, lib_names) """
    csv.field_size_limit(CSV_FIELD_LIMIT)
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            word = (row.get("word") or "").strip()
            if not WORD_RE.match(word) or len(word) > 30:
                continue

            tags = set((row.get("tag") or "").split())
            try:
                frq = int(row.get("frq") or 0)
            except ValueError:
                frq = 0

            lib_names = []
            for name, cond in LIBRARIES:
                if "tag" in cond and cond["tag"] in tags:
                    lib_names.append(name)
                elif "frq_top" in cond and 0 < frq <= cond["frq_top"]:
                    lib_names.append(name)
            if not lib_names:
                continue

            meanings = parse_meanings(row.get("translation") or "")
            if not meanings:
                continue

            phonetic = (row.get("phonetic") or "").strip()
            phonetic = f"[{phonetic}]"[:64] if phonetic else None
            yield word, phonetic, meanings, lib_names


def ensure_system_user(session) -> int:
    user = EnDesktopUser.select_one_by({"username": SYSTEM_USERNAME})
    if user:
        return user.id
    user = EnDesktopUser(username=SYSTEM_USERNAME, nickname="系统词库")
    session.add(user)
    session.flush()
    return user.id


def ensure_library(session, user_id: int, name: str, category: str = "考试词库") -> int:
    """category 写入 description，推荐页按它分组（考试词库/主题词库）"""
    lib = EnDesktopWordLibrary.select_one_by({"user_id": user_id, "name": name})
    if lib:
        if not lib.is_public:
            lib.is_public = 1
        if lib.description != category:
            lib.description = category
        return lib.id
    lib = EnDesktopWordLibrary(user_id=user_id, name=name, is_public=1, description=category)
    session.add(lib)
    session.flush()
    return lib.id


def main():
    parser = argparse.ArgumentParser()
    default_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecdict.csv")
    parser.add_argument("--csv", default=default_csv, help="ecdict.csv 路径，不存在则自动下载")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        download_csv(args.csv)

    session = SessionLocal()
    set_request_session(session)

    system_user_id = ensure_system_user(session)
    lib_ids = {name: ensure_library(session, system_user_id, name) for name, _ in LIBRARIES}
    session.commit()

    # 现有单词与词库条目一次载入内存做幂等（含软删条目，命中即恢复）
    word_ids = {w.word: w.id for w in session.query(EnDesktopWord).all()}
    existing_items = {}
    for item in session.query(EnDesktopWordLibraryItem).all():
        existing_items[(item.word_library_id, item.word_id)] = item

    # 自愈：释义里还残留字面量 \n 的词（早期版本没还原转义），重新解析替换。
    # 判断放在 Python 侧：LIKE 模式里反斜杠的转义在 MySQL 有歧义，容易误伤
    broken_word_ids = {
        m.word_id
        for m in session.query(EnDesktopWordMeaning).all()
        if "\\n" in (m.content or "")
    }

    stats = {"new_words": 0, "new_items": 0, "restored_items": 0, "repaired_words": 0}
    lib_counts = {name: 0 for name, _ in LIBRARIES}
    selected_words = set()
    pending = 0

    for word, phonetic, meanings, lib_names in wanted_rows(args.csv):
        selected_words.add(word)
        word_id = word_ids.get(word)
        if word_id is None:
            w = EnDesktopWord(word=word, en_pronunciation=phonetic, us_pronunciation=phonetic)
            session.add(w)
            session.flush()
            word_id = w.id
            word_ids[word] = word_id
            for m in meanings:
                session.add(
                    EnDesktopWordMeaning(word_id=word_id, type=m["type"], content=m["content"])
                )
            stats["new_words"] += 1
        elif word_id in broken_word_ids:
            session.query(EnDesktopWordMeaning).where(
                EnDesktopWordMeaning.word_id == word_id
            ).delete()
            for m in meanings:
                session.add(
                    EnDesktopWordMeaning(word_id=word_id, type=m["type"], content=m["content"])
                )
            broken_word_ids.discard(word_id)
            stats["repaired_words"] += 1

        for name in lib_names:
            lib_counts[name] += 1
            key = (lib_ids[name], word_id)
            item = existing_items.get(key)
            if item is None:
                item = EnDesktopWordLibraryItem(word_library_id=lib_ids[name], word_id=word_id)
                session.add(item)
                existing_items[key] = item
                stats["new_items"] += 1
            elif item.deleted_at is not None:
                item.deleted_at = None
                stats["restored_items"] += 1

        pending += 1
        if pending % 1000 == 0:
            session.commit()
            print(f"...已处理 {pending} 个词")

    session.commit()
    print("\n导入完成：")
    print(
        f"  新增单词 {stats['new_words']}，新增词库条目 {stats['new_items']}，"
        f"恢复条目 {stats['restored_items']}，修复释义 {stats['repaired_words']} 词"
    )
    print(f"  入选单词总数（去重）：{len(selected_words)}")
    for name, _ in LIBRARIES:
        print(f"  {name}: {lib_counts[name]} 词")


if __name__ == "__main__":
    main()
