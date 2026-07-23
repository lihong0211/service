#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""为 daily_expressions 生成 MP3，并回填 audio_url。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, set_request_session  # noqa: E402
from model.en_desktop import EnDesktopDailyExpression  # noqa: E402
from service.en_desktop.tencent_tts import synthesize_speech  # noqa: E402

STATIC_DIR = os.environ.get(
    "DAILY_EXPRESSION_AUDIO_STATIC_DIR", "/lihong/static/daily_expressions"
)
PUBLIC_BASE_URL = os.environ.get(
    "DAILY_EXPRESSION_AUDIO_PUBLIC_BASE_URL",
    "https://doctor-dog.com/static/daily_expressions",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 条缺音频的数据")
    parser.add_argument("--apply", action="store_true", help="生成文件并回填数据库")
    args = parser.parse_args()

    session = SessionLocal()
    set_request_session(session)

    query = (
        session.query(EnDesktopDailyExpression)
        .where(
            EnDesktopDailyExpression.deleted_at.is_(None),
            EnDesktopDailyExpression.audio_url.is_(None),
        )
        .order_by(EnDesktopDailyExpression.id.asc())
    )
    todo = query.limit(args.limit).all() if args.limit else query.all()

    if args.apply:
        os.makedirs(STATIC_DIR, exist_ok=True)

    stats = {"success": 0, "failed": 0}
    for expression in todo:
        audio = synthesize_speech(expression.phrase)
        if audio is None:
            print(f"跳过 #{expression.id}：TTS 调用失败，表达「{expression.phrase}」")
            stats["failed"] += 1
            continue

        audio_url = f"{PUBLIC_BASE_URL}/{expression.id}.mp3"
        tag = "[APPLY]" if args.apply else "[DRY-RUN]"
        print(f"{tag} #{expression.id} 「{expression.phrase}」 -> {audio_url}")
        if args.apply:
            file_path = os.path.join(STATIC_DIR, f"{expression.id}.mp3")
            with open(file_path, "wb") as file:
                file.write(audio)
            EnDesktopDailyExpression.update(
                {"id": expression.id, "audio_url": audio_url}
            )
        stats["success"] += 1

    session.close()
    print(f"\n完成：成功 {stats['success']}，跳过(TTS失败) {stats['failed']}")


if __name__ == "__main__":
    main()
