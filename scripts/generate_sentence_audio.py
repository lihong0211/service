#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为 word_sentences 表里还没有音频的例句生成 mp3、回填 audio_url。

用法：
    .venv/bin/python scripts/generate_sentence_audio.py                     # dry-run，处理全部缺音频的例句
    .venv/bin/python scripts/generate_sentence_audio.py --limit 20          # dry-run，只处理前 20 条（小样本试跑）
    .venv/bin/python scripts/generate_sentence_audio.py --limit 20 --apply  # 真正生成文件+写库

--dry-run 是默认行为（不加 --apply 就是 dry-run），跟 generate_phonics.py 的约定一致。

落地路径和对外 URL 默认指向生产服务器（要 SSH 上去跑），本地跑（用本地数据库+本地
uvicorn 当静态服务）可以用下面两个环境变量覆盖，跟 app/factory.py 挂载的 /static 保持一致：
    SENTENCE_AUDIO_STATIC_DIR=/Users/xxx/service-ali/static/word_sentences
    SENTENCE_AUDIO_PUBLIC_BASE_URL=http://localhost:3000/static/word_sentences
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, set_request_session  # noqa: E402
from model.en_desktop import EnDesktopWordSentence  # noqa: E402
from service.en_desktop.tencent_tts import synthesize_speech  # noqa: E402

STATIC_DIR = os.environ.get("SENTENCE_AUDIO_STATIC_DIR", "/lihong/static/word_sentences")
PUBLIC_BASE_URL = os.environ.get(
    "SENTENCE_AUDIO_PUBLIC_BASE_URL", "https://doctor-dog.com/static/word_sentences"
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=None, help="只处理前 N 条缺音频的例句，用于小样本试跑"
    )
    parser.add_argument("--apply", action="store_true", help="真正生成文件+写库，不加则只是 dry-run")
    parser.add_argument(
        "--workers", type=int, default=1, help="并发 TTS 请求数；数据库写入仍在主线程执行"
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers 必须大于等于 1")

    session = SessionLocal()
    set_request_session(session)

    query = (
        session.query(EnDesktopWordSentence)
        .where(
            EnDesktopWordSentence.deleted_at.is_(None),
            EnDesktopWordSentence.audio_url.is_(None),
        )
        .order_by(EnDesktopWordSentence.id.asc())
    )
    todo = query.limit(args.limit).all() if args.limit else query.all()

    if args.apply:
        os.makedirs(STATIC_DIR, exist_ok=True)

    items = [(s.id, s.en_text) for s in todo]

    def synthesize(item):
        sentence_id, en_text = item
        return sentence_id, en_text, synthesize_speech(en_text)

    executor = ThreadPoolExecutor(max_workers=args.workers) if args.workers > 1 else None
    results = executor.map(synthesize, items) if executor else map(synthesize, items)

    stats = {"success": 0, "failed": 0}
    for sentence_id, en_text, audio in results:
        if audio is None:
            print(f"跳过 #{sentence_id}：TTS 调用失败，例句「{en_text}」")
            stats["failed"] += 1
            continue

        audio_url = f"{PUBLIC_BASE_URL}/{sentence_id}.mp3"
        tag = "[APPLY]" if args.apply else "[DRY-RUN]"
        print(f"{tag} #{sentence_id} 「{en_text}」 -> {audio_url}")
        if args.apply:
            file_path = os.path.join(STATIC_DIR, f"{sentence_id}.mp3")
            with open(file_path, "wb") as f:
                f.write(audio)
            EnDesktopWordSentence.update({"id": sentence_id, "audio_url": audio_url})
        stats["success"] += 1

    if executor:
        executor.shutdown()

    print(f"\n完成：成功 {stats['success']}，跳过(TTS失败) {stats['failed']}")


if __name__ == "__main__":
    main()
