# 例句朗读(TTS) · 后端生成脚本 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 调有道智云语音合成 API，为 `word_sentences` 表里还没有音频的例句批量生成 mp3、回填 `audio_url`，并把例句数据接入现有单词/词库接口的返回结构。

**Architecture:** `service/en_desktop/youdao.py` 新增 `synthesize_speech()`，复用文件里已有的 v3 签名逻辑，换一个端点（语音合成而不是文本翻译）；离线脚本 `scripts/generate_sentence_audio.py` 遍历缺音频的例句、调用它、把 mp3 写到服务器本地 `/lihong/static/word_sentences/`、写回 `audio_url`，支持 `--dry-run`/`--apply`/`--limit`；`service/en_desktop/libraries.py` 里新增 `_sentences_grouped()`，接入 `_meanings_grouped`（libraries.py）和 `_meanings_of`（words.py），让每条 meaning 都带上对应例句。

**Tech Stack:** Python, FastAPI, SQLAlchemy 2.0, MySQL(`english_new` 库) / SQLite（测试用内存库），`requests`（已有依赖，不新增包），有道智云语音合成 API（`openapi.youdao.com/ttsapi`）

**关联文档:** [en-elctron 仓库的功能设计](/Users/lihong/Desktop/personal/code/en/en-elctron/docs/superpowers/specs/2026-07-22-sentence-tts-design.md) — 本计划覆盖设计文档里"一、二、三"三节（TTS 调用封装、生成脚本、API 序列化扩展）；"四、前端交互"是 en-elctron 仓库的独立计划。

## Global Constraints

- 有道智云语音合成端点 `https://openapi.youdao.com/ttsapi`，签名规则复用 `youdao.py` 里已有的 `_sign`/`_truncate`（`sha256(appKey + truncate(q) + salt + curtime + appSecret)`），AppKey/Secret 沿用 `.env` 里已有的 `YOUDAO_APP_KEY`/`YOUDAO_APP_SECRET`（当前给文本翻译用，需要确认有道智云后台已经给这对密钥开通"语音合成"产品）
- TTS 调用失败/接口报错/文本过长/未开通产品，一律返回 `None`，不抛异常；只有 AppKey/Secret 环境变量缺失时抛 `RuntimeError`（部署问题，不是单条例句的问题，沿用 `translate_to_chinese` 的先例）
- 生成脚本只处理 `word_sentences.audio_url IS NULL` 的行，`--dry-run`(默认)/`--apply`/`--limit`，失败的例句跳过打日志，不重试、不写脏数据
- mp3 落地路径固定为服务器本地 `/lihong/static/word_sentences/<sentence_id>.mp3`，对应 `audio_url = f"https://doctor-dog.com/static/word_sentences/{id}.mp3"`（复用 nginx 已有的 `location ^~ /static/` alias，这个 alias 挂在 `doctor-dog.com` 这个 server block 下，不需要改 nginx 配置）
- 生成脚本要在服务器上跑（SSH 上去，和 `deploy.sh` 部署的目标机器一致）——数据库远程直连没问题，但静态文件必须落在服务器本地磁盘，本地生成再传没必要多写一道 rsync
- API 序列化不新开端点：在 `service/en_desktop/words.py::_meanings_of` 和 `service/en_desktop/libraries.py::_meanings_grouped` 里给每条 meaning 加一个 `sentence` 字段，值是 `{"en_text": str, "zh_text": str, "audio_url": str | None}` 或 `None`（该 meaning 还没有对应例句时）
- 不重新生成已经有 `audio_url` 的例句

---

### Task 1: 有道智云语音合成调用封装

**Files:**
- Modify: `service/en_desktop/youdao.py`
- Test: `tests/en_desktop/test_youdao_tts.py`

**Interfaces:**
- Consumes: 文件内已有的 `_sign(app_key, app_secret, q, salt, curtime) -> str`、`_truncate(q) -> str`（无需改动，直接复用）
- Produces: `synthesize_speech(text: str, voice_name: str = "youxiaomei") -> bytes | None`，供 Task 2 的生成脚本调用

- [ ] **Step 1: 写失败测试**

```python
# tests/en_desktop/test_youdao_tts.py
"""
有道智云语音合成 (TTS) API 调用测试：mock requests.post，不打真实网络请求
"""
import pytest

from service.en_desktop import youdao


class _FakeResponse:
    def __init__(self, status_code, headers, content=b"", json_data=None, text=""):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


def test_synthesize_speech_success(monkeypatch):
    monkeypatch.setenv("YOUDAO_APP_KEY", "test-key")
    monkeypatch.setenv("YOUDAO_APP_SECRET", "test-secret")
    fake_audio = b"FAKE_MP3_BYTES"
    monkeypatch.setattr(
        youdao.requests,
        "post",
        lambda *a, **kw: _FakeResponse(200, {"Content-Type": "audio/mp3"}, content=fake_audio),
    )

    result = youdao.synthesize_speech("Hello world.")
    assert result == fake_audio


def test_synthesize_speech_error_body_returns_none(monkeypatch):
    monkeypatch.setenv("YOUDAO_APP_KEY", "test-key")
    monkeypatch.setenv("YOUDAO_APP_SECRET", "test-secret")
    monkeypatch.setattr(
        youdao.requests,
        "post",
        lambda *a, **kw: _FakeResponse(
            200,
            {"Content-Type": "application/json"},
            json_data={"errorCode": "110"},
            text='{"errorCode": "110"}',
        ),
    )

    assert youdao.synthesize_speech("Hello world.") is None


def test_synthesize_speech_http_error_returns_none(monkeypatch):
    monkeypatch.setenv("YOUDAO_APP_KEY", "test-key")
    monkeypatch.setenv("YOUDAO_APP_SECRET", "test-secret")
    monkeypatch.setattr(
        youdao.requests, "post", lambda *a, **kw: _FakeResponse(500, {}, text="server error")
    )

    assert youdao.synthesize_speech("Hello world.") is None


def test_synthesize_speech_network_exception_returns_none(monkeypatch):
    monkeypatch.setenv("YOUDAO_APP_KEY", "test-key")
    monkeypatch.setenv("YOUDAO_APP_SECRET", "test-secret")

    def _raise(*a, **kw):
        raise youdao.requests.exceptions.ReadTimeout("timed out")

    monkeypatch.setattr(youdao.requests, "post", _raise)
    assert youdao.synthesize_speech("Hello world.") is None


def test_synthesize_speech_missing_api_key(monkeypatch):
    monkeypatch.delenv("YOUDAO_APP_KEY", raising=False)
    monkeypatch.delenv("YOUDAO_APP_SECRET", raising=False)

    with pytest.raises(RuntimeError):
        youdao.synthesize_speech("Hello world.")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/bin/pytest tests/en_desktop/test_youdao_tts.py -v`
Expected: FAIL — `AttributeError: module 'service.en_desktop.youdao' has no attribute 'synthesize_speech'`

- [ ] **Step 3: 实现**

在 `service/en_desktop/youdao.py` 末尾追加（`hashlib`/`logging`/`os`/`time`/`uuid`/`requests` 都已经在文件顶部导入，不用新加 import）：

```python
YOUDAO_TTS_URL = "https://openapi.youdao.com/ttsapi"


def synthesize_speech(text: str, voice_name: str = "youxiaomei") -> bytes | None:
    """
    调有道智云语音合成 API，返回 mp3 二进制。
    请求异常、HTTP 报错、返回内容不是音频（未开通语音合成产品/账户欠费/文本过长等）
    都归一为返回 None，不抛异常——生成脚本按 None 跳过该条例句，不重试。
    """
    app_key = os.getenv("YOUDAO_APP_KEY")
    app_secret = os.getenv("YOUDAO_APP_SECRET")
    if not app_key or not app_secret:
        raise RuntimeError("未配置 YOUDAO_APP_KEY / YOUDAO_APP_SECRET")

    salt = str(uuid.uuid4())
    curtime = str(int(time.time()))
    sign = _sign(app_key, app_secret, text, salt, curtime)

    try:
        resp = requests.post(
            YOUDAO_TTS_URL,
            data={
                "q": text,
                "appKey": app_key,
                "salt": salt,
                "sign": sign,
                "signType": "v3",
                "curtime": curtime,
                "voiceName": voice_name,
                "format": "mp3",
            },
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        logger.error("有道语音合成请求异常: %s", e)
        return None

    content_type = resp.headers.get("Content-Type", "")
    if resp.status_code == 200 and content_type.startswith("audio"):
        return resp.content

    logger.error(
        "有道语音合成API报错: status=%s content_type=%s body=%s",
        resp.status_code,
        content_type,
        resp.text[:200],
    )
    return None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/bin/pytest tests/en_desktop/test_youdao_tts.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: Commit**

```bash
git add service/en_desktop/youdao.py tests/en_desktop/test_youdao_tts.py
git commit -m "feat: 新增有道智云语音合成调用封装 synthesize_speech"
```

---

### Task 2: 例句音频生成脚本

**Files:**
- Create: `scripts/generate_sentence_audio.py`
- Modify: `.env.example`

**Interfaces:**
- Consumes: `EnDesktopWordSentence`（`model/en_desktop`，已存在）、`synthesize_speech`（Task 1）
- Produces: 无（脚本，本身不被其他代码 import）

这一步是胶水脚本，跟 `scripts/generate_phonics.py` 一样不写自动化单测——脚本本身用 Task 3 的小样本试跑来验证。

- [ ] **Step 1: `.env.example` 补上 Youdao 密钥说明**

`YOUDAO_APP_KEY`/`YOUDAO_APP_SECRET` 已经在真实 `.env` 里配置（给 `translate_to_chinese` 用），但 `.env.example` 里一直没写。在 `.env.example` 里追加：

```
# 有道智云 API：查词翻译（service/en_desktop/youdao.py::translate_to_chinese）和
# 例句朗读生成脚本（scripts/generate_sentence_audio.py）共用同一对密钥，
# 需要确认有道智云后台已经给这对密钥开通"语音合成"产品
YOUDAO_APP_KEY=
YOUDAO_APP_SECRET=
```

- [ ] **Step 2: 写脚本**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为 word_sentences 表里还没有音频的例句生成 mp3、回填 audio_url。

用法：
    .venv/bin/python scripts/generate_sentence_audio.py                     # dry-run，处理全部缺音频的例句
    .venv/bin/python scripts/generate_sentence_audio.py --limit 20          # dry-run，只处理前 20 条（小样本试跑）
    .venv/bin/python scripts/generate_sentence_audio.py --limit 20 --apply  # 真正生成文件+写库

--dry-run 是默认行为（不加 --apply 就是 dry-run），跟 generate_phonics.py 的约定一致。
必须在服务器上跑（SSH 上去）：mp3 要落在服务器本地磁盘的 STATIC_DIR，本地没有这个路径。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, set_request_session  # noqa: E402
from model.en_desktop import EnDesktopWordSentence  # noqa: E402
from service.en_desktop.youdao import synthesize_speech  # noqa: E402

STATIC_DIR = "/lihong/static/word_sentences"
PUBLIC_BASE_URL = "https://doctor-dog.com/static/word_sentences"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=None, help="只处理前 N 条缺音频的例句，用于小样本试跑"
    )
    parser.add_argument("--apply", action="store_true", help="真正生成文件+写库，不加则只是 dry-run")
    args = parser.parse_args()

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

    stats = {"success": 0, "failed": 0}
    for s in todo:
        audio = synthesize_speech(s.en_text)
        if audio is None:
            print(f"跳过 #{s.id}：TTS 调用失败，例句「{s.en_text}」")
            stats["failed"] += 1
            continue

        audio_url = f"{PUBLIC_BASE_URL}/{s.id}.mp3"
        tag = "[APPLY]" if args.apply else "[DRY-RUN]"
        print(f"{tag} #{s.id} 「{s.en_text}」 -> {audio_url}")
        if args.apply:
            file_path = os.path.join(STATIC_DIR, f"{s.id}.mp3")
            with open(file_path, "wb") as f:
                f.write(audio)
            EnDesktopWordSentence.update({"id": s.id, "audio_url": audio_url})
        stats["success"] += 1

    print(f"\n完成：成功 {stats['success']}，跳过(TTS失败) {stats['failed']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_sentence_audio.py .env.example
git commit -m "feat: 新增例句音频生成脚本 generate_sentence_audio.py"
```

---

### Task 3: 小样本试跑与人工验证

**Files:** 无代码改动，纯手动执行验证

- [ ] **Step 1: 确认有道智云后台已开通语音合成产品**

登录有道智云控制台，确认现有 AppKey 对应的应用已经开通"语音合成"产品（不是只有"文本翻译"）。没开通的话先去申请，否则 Task 3 Step 2 会全部失败。

- [ ] **Step 2: SSH 到服务器，dry-run 小样本看质量**

```bash
ssh <user>@<server>   # 用 .env 里的 DEPLOY_HOST/DEPLOY_USER，跟 deploy.sh 一致
cd <DEPLOY_PATH>
.venv/bin/python scripts/generate_sentence_audio.py --limit 10
```

Expected: 打印 10 条 `[DRY-RUN] #id 「例句」 -> https://doctor-dog.com/static/word_sentences/<id>.mp3`。如果全部跳过（TTS 调用失败），先回去检查 Step 1 的产品开通状态。

- [ ] **Step 3: 确认后写文件+写库**

```bash
.venv/bin/python scripts/generate_sentence_audio.py --limit 10 --apply
```

Expected: 打印 `[APPLY]` 而不是 `[DRY-RUN]`，末尾统计成功数量；`ls /lihong/static/word_sentences/` 能看到对应的 `<id>.mp3` 文件。

- [ ] **Step 4: 浏览器打开 audio_url，人工听一遍**

打开 `https://doctor-dog.com/static/word_sentences/<某个id>.mp3`，确认能正常播放、发音清晰、语速正常。

- [ ] **Step 5: 查库确认 audio_url 已回填**

```bash
mysql -h localhost -u root -p english_new -e "SELECT id, en_text, audio_url FROM word_sentences WHERE audio_url IS NOT NULL LIMIT 10;"
```

Expected: 能看到 10 条记录，`audio_url` 是完整可访问的 URL。

- [ ] **Step 6: 视质量决定是否放开跑全量**

样本质量满意后，再决定是否去掉 `--limit` 跑全量；例句数量大的话建议分批跑（比如每次 `--limit 500`），观察失败率和有道 TTS 每小时 3000 次请求的限额。这一步不写进本计划的自动化范围，由你根据实际样本结果决定。

---

### Task 4: API 序列化扩展——meaning 挂上 sentence 字段

**Files:**
- Modify: `service/en_desktop/libraries.py`
- Modify: `service/en_desktop/words.py`
- Modify: `tests/en_desktop/test_words.py:19`
- Test: `tests/en_desktop/test_libraries.py`（追加用例）、`tests/en_desktop/test_words.py`（追加用例）

**Interfaces:**
- Consumes: `EnDesktopWordSentence`（`model/en_desktop`，已存在）
- Produces: `_sentences_grouped(meaning_ids: list) -> dict`（`libraries.py`，`word_meaning_id -> {en_text, zh_text, audio_url}`），供 `_meanings_grouped`/`_meanings_of` 内部使用；两者返回的 meaning 字典新增 `sentence` 键，字面量结构变为 `{"type": str, "content": str, "sentence": {"en_text": str, "zh_text": str, "audio_url": str | None} | None}`——en-elctron 前端的实施计划直接消费这个结构

- [ ] **Step 1: 追加失败测试（libraries.py 的 `_meanings_grouped`）**

在 `tests/en_desktop/test_libraries.py` 末尾追加：

```python
from model.en_desktop import EnDesktopWordMeaning, EnDesktopWordSentence


def test_library_words_meaning_carries_sentence(user_id):
    word_id = _add_word("apple")
    lib_id = libraries.list_libraries(user_id)["data"][0]["id"]
    libraries.add_item(lib_id, word_id)

    meaning = EnDesktopWordMeaning.select_by({"word_id": word_id})[0]
    EnDesktopWordSentence.insert(
        {
            "word_meaning_id": meaning.id,
            "en_text": "I ate an apple.",
            "zh_text": "我吃了一个苹果。",
            "audio_url": "https://doctor-dog.com/static/word_sentences/1.mp3",
        }
    )

    result = libraries.library_words(user_id, lib_id)
    word = result["data"]["list"][0]
    assert word["meaning"][0]["sentence"] == {
        "en_text": "I ate an apple.",
        "zh_text": "我吃了一个苹果。",
        "audio_url": "https://doctor-dog.com/static/word_sentences/1.mp3",
    }


def test_library_words_meaning_without_sentence_is_none(user_id):
    word_id = _add_word("banana")
    lib_id = libraries.list_libraries(user_id)["data"][0]["id"]
    libraries.add_item(lib_id, word_id)

    result = libraries.library_words(user_id, lib_id)
    word = result["data"]["list"][0]
    assert word["meaning"][0]["sentence"] is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/bin/pytest tests/en_desktop/test_libraries.py -v -k sentence`
Expected: FAIL — `assert None == {...}` 或 `KeyError: 'sentence'`（`_meanings_grouped` 还没加这个字段）

- [ ] **Step 3: 实现 `_sentences_grouped` 并接入 `_meanings_grouped`**

在 `service/en_desktop/libraries.py`，`import` 部分把 `EnDesktopWordSentence` 加进已有的 `from model.en_desktop import (...)`：

```python
from model.en_desktop import (
    EnDesktopWord,
    EnDesktopWordLibrary,
    EnDesktopWordLibraryFavorite,
    EnDesktopWordLibraryItem,
    EnDesktopWordMeaning,
    EnDesktopWordSentence,
)
```

在 `_meanings_grouped` 函数前面新增：

```python
def _sentences_grouped(meaning_ids: list) -> dict:
    """word_meaning_id -> {en_text, zh_text, audio_url}，一次查询代替逐条查询"""
    grouped = {}
    if not meaning_ids:
        return grouped
    rows = (
        db.session.query(EnDesktopWordSentence)
        .where(
            EnDesktopWordSentence.word_meaning_id.in_(meaning_ids),
            EnDesktopWordSentence.deleted_at.is_(None),
        )
        .all()
    )
    for s in rows:
        grouped[s.word_meaning_id] = {
            "en_text": s.en_text,
            "zh_text": s.zh_text,
            "audio_url": s.audio_url,
        }
    return grouped
```

把 `_meanings_grouped` 函数体替换为：

```python
def _meanings_grouped(word_ids: list) -> dict:
    """word_id -> [{type, content, sentence}]，一次查询代替逐词查询"""
    grouped = {}
    if not word_ids:
        return grouped
    rows = (
        db.session.query(EnDesktopWordMeaning)
        .where(
            EnDesktopWordMeaning.word_id.in_(word_ids),
            EnDesktopWordMeaning.deleted_at.is_(None),
        )
        .order_by(EnDesktopWordMeaning.id.asc())
        .all()
    )
    sentences = _sentences_grouped([m.id for m in rows])
    for m in rows:
        grouped.setdefault(m.word_id, []).append(
            {"type": m.type, "content": m.content, "sentence": sentences.get(m.id)}
        )
    return grouped
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/bin/pytest tests/en_desktop/test_libraries.py -v -k sentence`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add service/en_desktop/libraries.py tests/en_desktop/test_libraries.py
git commit -m "feat: library_words 返回的 meaning 挂上对应例句"
```

- [ ] **Step 6: 追加失败测试（words.py 的 `_meanings_of`）**

在 `tests/en_desktop/test_words.py` 末尾追加：

```python
from model.en_desktop import EnDesktopWordSentence


def test_get_word_meaning_carries_sentence(en_desktop_db):
    word_id = words.add_word(dict(WORD_PAYLOAD))["data"]["id"]
    meaning = EnDesktopWordMeaning.select_by({"word_id": word_id})[0]
    EnDesktopWordSentence.insert(
        {
            "word_meaning_id": meaning.id,
            "en_text": "I ate an apple.",
            "zh_text": "我吃了一个苹果。",
            "audio_url": None,
        }
    )

    result = words.get_word(word_id)
    assert result["data"]["meaning"][0]["sentence"] == {
        "en_text": "I ate an apple.",
        "zh_text": "我吃了一个苹果。",
        "audio_url": None,
    }
```

同时修正 `test_add_and_get_word` 里因为字段新增而过时的精确匹配断言（第 19 行），把：

```python
    assert result["data"]["meaning"] == [{"type": "n.", "content": "苹果"}]
```

改成：

```python
    assert result["data"]["meaning"] == [
        {"type": "n.", "content": "苹果", "sentence": None}
    ]
```

- [ ] **Step 7: 运行测试确认失败**

Run: `.venv/bin/pytest tests/en_desktop/test_words.py -v`
Expected: `test_get_word_meaning_carries_sentence` FAIL（`KeyError: 'sentence'`）；`test_add_and_get_word` 这一条这时候也还是 FAIL（断言已经改成新格式，但实现没跟上）

- [ ] **Step 8: 实现 `_meanings_of` 接入**

`service/en_desktop/words.py` 顶部的 import 改成同时引入 `_sentences_grouped`：

```python
from service.en_desktop.libraries import _meanings_grouped, _sentences_grouped
```

把 `_meanings_of` 函数体替换为：

```python
def _meanings_of(word_id: int) -> list:
    meanings = EnDesktopWordMeaning.select_by({"word_id": word_id})
    sentences = _sentences_grouped([m.id for m in meanings])
    return [
        {"type": m.type, "content": m.content, "sentence": sentences.get(m.id)}
        for m in meanings
    ]
```

- [ ] **Step 9: 运行测试确认通过**

Run: `.venv/bin/pytest tests/en_desktop/test_words.py -v`
Expected: PASS（全部通过，含新增的 `test_get_word_meaning_carries_sentence` 和改过的 `test_add_and_get_word`）

- [ ] **Step 10: 全量跑一遍 en_desktop 测试确认没有连带破坏**

Run: `.venv/bin/pytest tests/en_desktop/ -v`
Expected: 全部 PASS

- [ ] **Step 11: Commit**

```bash
git add service/en_desktop/words.py tests/en_desktop/test_words.py
git commit -m "feat: get_word/list_words 返回的 meaning 挂上对应例句"
```

## Self-Review

- **Spec 覆盖**：本计划覆盖了 en-elctron 设计文档"一、TTS 调用封装"、"二、生成脚本"、"三、API 序列化扩展"三节的全部内容（签名复用、失败归一返回 None、`--dry-run`/`--apply`/`--limit`、静态文件路径与 nginx alias 复用、`sentence` 字段挂载到 `_meanings_of`/`_meanings_grouped`）。"四、前端交互"不在本计划范围内，是 en-elctron 仓库的独立计划。
- **占位符检查**：所有代码块都是完整实现，没有 TBD/TODO。
- **类型一致性**：`_sentences_grouped` 返回的 `{en_text, zh_text, audio_url}` 结构，在 `_meanings_grouped`、`_meanings_of` 两处接入方式一致；`sentence` 字段无例句时统一是 `None`（不是空字典或空字符串），前端计划据此判断是否显示播放按钮。
- **既有测试连带影响**：确认了只有 `test_words.py:19`（`test_add_and_get_word` 的精确匹配断言）会因为新增字段而过时，已在 Task 4 Step 6 里一并修正；`test_libraries.py`/`test_words.py` 里其它涉及 `meaning` 的断言都是输入 payload 或长度/真值检查，不受影响。
