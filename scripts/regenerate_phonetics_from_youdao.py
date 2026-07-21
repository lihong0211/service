#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用有道词典公开接口（service.en_desktop.youdao.fetch_phonetic）重新生成
words 表的英/美音标，让两者真正区分开（现在库里绝大多数词的 en/us 是同一个值）。

查不到的词保留原值不动——原值已经是标准 Unicode IPA（经 normalize_phonetics.py
清理过），只是可能不区分英美，不算坏数据，不强求。

用法：
    .venv/bin/python scripts/regenerate_phonetics_from_youdao.py                 # dry-run，全部词
    .venv/bin/python scripts/regenerate_phonetics_from_youdao.py --limit 50      # dry-run，小样本
    .venv/bin/python scripts/regenerate_phonetics_from_youdao.py --limit 50 --apply  # 真正写库

写库前务必先手动备份：
    mysqldump -h <host> -u <user> -p english_new words > words_backup_youdao_$(date +%Y%m%d).sql
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, set_request_session  # noqa: E402
from model.en_desktop import EnDesktopWord  # noqa: E402
from service.en_desktop.youdao import fetch_phonetic  # noqa: E402


def _format(phone: str) -> str:
    """
    去掉有道音标里表示可选音的圆括号（保留括号里的内容），套上方括号跟库里现有记法一致。
    少数虚词（如 "a"）有道会给多个变体用 "; " 或 ", " 隔开（重读式/弱读式），只取第一个
    作为唯一的规范读音，跟单词表原有"一个词一个音标"的假设保持一致。
    """
    primary = phone.split(";")[0].split(",")[0].strip()
    return f"[{primary.replace('(', '').replace(')', '')}]"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 个词，用于小样本试跑")
    parser.add_argument("--apply", action="store_true", help="真正写库，不加则只是 dry-run")
    args = parser.parse_args()

    session = SessionLocal()
    set_request_session(session)

    query = (
        session.query(EnDesktopWord)
        .where(EnDesktopWord.deleted_at.is_(None))
        .order_by(EnDesktopWord.id.asc())
    )
    words = query.limit(args.limit).all() if args.limit else query.all()

    stats = {"updated": 0, "not_found": 0}
    tag = "[APPLY]" if args.apply else "[DRY-RUN]"
    for w in words:
        result = fetch_phonetic(w.word)
        if not result:
            stats["not_found"] += 1
            print(f"[查不到，保留原值] {w.word}")
            time.sleep(0.1)
            continue

        new_en = _format(result["en_pronunciation"])
        new_us = _format(result["us_pronunciation"])
        print(f"{tag} {w.word}: en {w.en_pronunciation} -> {new_en} | us {w.us_pronunciation} -> {new_us}")
        if args.apply:
            w.en_pronunciation = new_en
            w.us_pronunciation = new_us
        stats["updated"] += 1
        time.sleep(0.1)

    if args.apply:
        session.commit()

    print(f"\n完成：更新 {stats['updated']}，查不到保留原值 {stats['not_found']}")


if __name__ == "__main__":
    main()
