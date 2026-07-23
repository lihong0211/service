# 拼读拆分 · 后端生成脚本 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `words` 表里的单词生成"字母段-音素"拼读拆分数据，存入新表 `word_phonics`，先在小样本上跑通并人工验证质量。

**Architecture:** 新增 `word_phonics` 表（word_id 唯一，segments 是 JSON 数组）；一个纯函数模块负责 IPA 分词与拆分结果校验（无外部依赖，可单测）；一个 LLM 调用模块封装 DashScope（阿里百炼）OpenAI 兼容接口；一个离线脚本 `scripts/generate_phonics.py` 把两者粘合起来，遍历缺失拼读数据的词、调用 LLM、校验、写库，支持 `--dry-run`/`--apply`/`--limit`。

**Tech Stack:** Python, FastAPI, SQLAlchemy 2.0, MySQL(`english_new` 库) / SQLite（测试用内存库），`requests`（已有依赖，不新增包），DashScope OpenAI 兼容接口（`qwen-plus`）

**关联文档:** [en-elctron 仓库的功能设计](/Users/lihong/Desktop/personal/code/en/en-elctron/docs/superpowers/specs/2026-07-19-phonics-breakdown-design.md) — 本计划只覆盖设计文档里"一、二"两节（后端数据模型 + 生成脚本），API 扩展和前端部分是后续独立计划。

## Global Constraints

- `segments` 每段结构固定为 `{"letters": "...", "ipa": "..."}`
- 硬校验规则（生成脚本里，校验不通过的词整词跳过、不写入、只打日志，不重试、不写脏数据）：
  1. 所有 `letters` 依次拼接（忽略大小写）必须等于原词
  2. 所有 `ipa` 依次拼接、去掉 `/ ˈ ˌ .` 和空格后，必须等于原始音标同样处理后的结果
  3. 每一段的 `ipa` 必须能被音素清单完整分词（清单外符号视为不合法）
- `word_phonics.word_id` 用有符号 `INT`（不是 `INT UNSIGNED`），匹配 `words.id` 的真实列类型（参考 `sql/en_desktop_word_sentences.sql` 里的说明）
- 不新增 pip 依赖：LLM 调用直接用已有的 `requests` 库走 HTTP，不引入 `openai`/`dashscope` SDK
- LLM 用 DashScope 的 OpenAI 兼容接口：`https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`，模型 `qwen-plus`，鉴权用环境变量 `DASHSCOPE_API_KEY`（Bearer token），用 `response_format: {"type": "json_object"}` 强制 JSON 输出
- 脚本遵循仓库里 `scripts/import_ecdict.py` 的 SQLAlchemy session 用法（`SessionLocal()` + `set_request_session()`），不用 `rebuild_roots_affixes.py` 那种独立 pymysql 连接的写法

---

### Task 1: `word_phonics` 表 + 模型

**Files:**
- Create: `sql/en_desktop_word_phonics.sql`
- Create: `model/en_desktop/word_phonics.py`
- Modify: `model/en_desktop/__init__.py`
- Test: `tests/en_desktop/test_word_phonics.py`

**Interfaces:**
- Produces: `EnDesktopWordPhonics`（字段 `id`、`word_id`、`segments`、`created_at`、`updated_at`、`deleted_at`），供 Task 5 的生成脚本 `session.add(EnDesktopWordPhonics(word_id=..., segments=...))` 使用

- [ ] **Step 1: 写 SQL 迁移文件**

```sql
-- sql/en_desktop_word_phonics.sql
-- en-desktop 单词拼读拆分表（字母段-音素对应关系，AI 生成，供拼读教学功能使用）
-- 用法：mysql -h <host> -u <user> -p english_new < sql/en_desktop_word_phonics.sql
-- word_id 用有符号 INT，匹配 words.id 实际列类型（同 en_desktop_word_sentences.sql 的约定）

CREATE TABLE IF NOT EXISTS word_phonics (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  word_id     INT NOT NULL COMMENT '单词ID',
  segments    JSON NOT NULL COMMENT '字母段-音素拆分，如 [{"letters":"c","ipa":"k"},...]',
  created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at  DATETIME     NULL COMMENT '软删除时间',
  UNIQUE KEY uk_word_id (word_id),
  CONSTRAINT fk_word_phonics_word_id FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单词拼读拆分（字母段-音素对应，AI 生成）';
```

- [ ] **Step 2: 写模型的失败测试**

```python
# tests/en_desktop/test_word_phonics.py
"""
en-desktop 拼读拆分模型测试
"""
import pytest
from sqlalchemy.exc import IntegrityError

from model.en_desktop import EnDesktopWordPhonics


def test_insert_and_query_word_phonics(en_desktop_db):
    segments = [
        {"letters": "c", "ipa": "k"},
        {"letters": "a", "ipa": "æ"},
        {"letters": "t", "ipa": "t"},
    ]
    en_desktop_db.add(EnDesktopWordPhonics(word_id=1, segments=segments))
    en_desktop_db.commit()

    row = (
        en_desktop_db.query(EnDesktopWordPhonics)
        .where(EnDesktopWordPhonics.word_id == 1)
        .first()
    )
    assert row.segments == segments


def test_word_id_unique_constraint(en_desktop_db):
    en_desktop_db.add(EnDesktopWordPhonics(word_id=1, segments=[{"letters": "a", "ipa": "a"}]))
    en_desktop_db.commit()

    en_desktop_db.add(EnDesktopWordPhonics(word_id=1, segments=[{"letters": "b", "ipa": "b"}]))
    with pytest.raises(IntegrityError):
        en_desktop_db.commit()
```

- [ ] **Step 3: 运行测试确认失败**

Run: `.venv/bin/pytest tests/en_desktop/test_word_phonics.py -v`
Expected: FAIL — `ImportError: cannot import name 'EnDesktopWordPhonics'`（模型还没定义）

- [ ] **Step 4: 写模型**

```python
# model/en_desktop/word_phonics.py
"""
en-desktop 单词拼读拆分模型（english_new.word_phonics）
每个单词最多一条记录（word_id 唯一），segments 是 AI 生成并校验过的字母段-音素对齐结果。
"""
from sqlalchemy import Column, ForeignKey, Integer, JSON

from model.en_desktop.base import BaseEnDesktop, EnDesktopModel


class EnDesktopWordPhonics(BaseEnDesktop, EnDesktopModel):
    __tablename__ = "word_phonics"

    word_id = Column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    segments = Column(JSON, nullable=False)
```

- [ ] **Step 5: 注册到 `__init__.py`**

在 `model/en_desktop/__init__.py` 里，`word_meanings` 导入之后、`word_sentences` 导入之前插入：

```python
from .word_meanings import EnDesktopWordMeaning
from .word_phonics import EnDesktopWordPhonics
from .word_sentences import EnDesktopWordSentence
```

`__all__` 列表里，在 `"EnDesktopWordMeaning"` 之后加一行：

```python
    "EnDesktopWordMeaning",
    "EnDesktopWordPhonics",
    "EnDesktopWordSentence",
```

- [ ] **Step 6: 运行测试确认通过**

Run: `.venv/bin/pytest tests/en_desktop/test_word_phonics.py -v`
Expected: PASS（2 passed）

- [ ] **Step 7: Commit**

```bash
git add sql/en_desktop_word_phonics.sql model/en_desktop/word_phonics.py model/en_desktop/__init__.py tests/en_desktop/test_word_phonics.py
git commit -m "feat: 新增 word_phonics 表与模型，用于单词拼读拆分数据"
```

---

### Task 2: IPA 音素清单 + 分词器

**Files:**
- Create: `service/en_desktop/phonics.py`
- Test: `tests/en_desktop/test_phonics.py`

**Interfaces:**
- Produces: `normalize_ipa(ipa: str) -> str`、`tokenize_ipa(ipa: str) -> list[str] | None`、`PHONEMES: list[str]` —— Task 3 的 `validate_segments` 会用到 `normalize_ipa`/`tokenize_ipa`；Task 5 的脚本只用 `validate_segments`（来自 Task 3），不直接用这两个函数

- [ ] **Step 1: 写失败测试**

```python
# tests/en_desktop/test_phonics.py
"""
拼读拆分：IPA 分词与校验逻辑测试（纯函数，不依赖数据库）
"""
from service.en_desktop.phonics import normalize_ipa, tokenize_ipa


def test_normalize_ipa_strips_slashes_stress_and_dots():
    assert normalize_ipa("/ˈæp.əl/") == "æpəl"


def test_tokenize_ipa_regular_word():
    assert tokenize_ipa("/kæt/") == ["k", "æ", "t"]


def test_tokenize_ipa_handles_affricate_and_diphthong():
    assert tokenize_ipa("/tʃeɪr/") == ["tʃ", "eɪ", "r"]


def test_tokenize_ipa_unknown_symbol_returns_none():
    assert tokenize_ipa("/k@t/") is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/bin/pytest tests/en_desktop/test_phonics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'service.en_desktop.phonics'`

- [ ] **Step 3: 实现**

```python
# service/en_desktop/phonics.py
"""
拼读拆分：IPA 音素清单、分词、字母-音素对齐结果校验。
供 scripts/generate_phonics.py 校验 LLM 返回结果用。
"""
import re

# 英语 IPA 音素清单（含双元音、塞擦音等多字符符号）。
# 按长度降序排列供最长匹配分词使用——不能按字母表排序，"tʃ" 必须排在 "t" 前面。
PHONEMES = sorted(
    [
        # 塞擦音
        "tʃ", "dʒ",
        # 双元音 / r 化元音（多字符，优先匹配）
        "eɪ", "aɪ", "ɔɪ", "aʊ", "oʊ", "əʊ", "ɪə", "eə", "ʊə",
        "ɑːr", "ɔːr", "ɜːr", "ɪr", "ɛr", "ʊr",
        # 长元音
        "iː", "ɑː", "ɔː", "uː", "ɜː",
        # 单元音
        "ɪ", "e", "æ", "ʌ", "ɒ", "ʊ", "ə", "ɝ", "ɚ",
        # 辅音
        "p", "b", "t", "d", "k", "g", "f", "v", "θ", "ð",
        "s", "z", "ʃ", "ʒ", "h", "m", "n", "ŋ", "l", "r", "j", "w",
    ],
    key=len,
    reverse=True,
)

# 音标里忽略的装饰符号：斜杠、重音符 ˈˌ、音节分隔点、空格
_STRIP_RE = re.compile(r"[/ˈˌ.\s]")


def normalize_ipa(ipa: str) -> str:
    """去掉 /.../ 包裹、重音符 ˈˌ、音节分隔点 . 和空格"""
    return _STRIP_RE.sub("", ipa or "")


def tokenize_ipa(ipa: str) -> list[str] | None:
    """按 PHONEMES 最长匹配把 IPA 字符串切成音素列表；遇到清单外的符号返回 None"""
    text = normalize_ipa(ipa)
    tokens = []
    i = 0
    while i < len(text):
        for p in PHONEMES:
            if text.startswith(p, i):
                tokens.append(p)
                i += len(p)
                break
        else:
            return None
    return tokens
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/bin/pytest tests/en_desktop/test_phonics.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add service/en_desktop/phonics.py tests/en_desktop/test_phonics.py
git commit -m "feat: 新增 IPA 音素清单与分词器"
```

---

### Task 3: 拆分结果校验

**Files:**
- Modify: `service/en_desktop/phonics.py`
- Test: `tests/en_desktop/test_phonics.py`

**Interfaces:**
- Consumes: `normalize_ipa`、`tokenize_ipa`（Task 2，同文件内）
- Produces: `validate_segments(word: str, ipa: str, segments: list) -> bool` —— Task 5 的生成脚本用它决定 LLM 返回结果是否写库

- [ ] **Step 1: 追加失败测试**

在 `tests/en_desktop/test_phonics.py` 末尾追加：

```python
from service.en_desktop.phonics import validate_segments


def test_validate_segments_valid():
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "a", "ipa": "æ"}, {"letters": "t", "ipa": "t"}]
    assert validate_segments("cat", "/kæt/", segments) is True


def test_validate_segments_letters_mismatch():
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "o", "ipa": "æ"}, {"letters": "t", "ipa": "t"}]
    assert validate_segments("cat", "/kæt/", segments) is False


def test_validate_segments_ipa_mismatch():
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "a", "ipa": "e"}, {"letters": "t", "ipa": "t"}]
    assert validate_segments("cat", "/kæt/", segments) is False


def test_validate_segments_rejects_unknown_ipa_symbol():
    segments = [{"letters": "ca", "ipa": "k@"}, {"letters": "t", "ipa": "t"}]
    assert validate_segments("cat", "/k@t/", segments) is False


def test_validate_segments_empty_list_is_invalid():
    assert validate_segments("cat", "/kæt/", []) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/bin/pytest tests/en_desktop/test_phonics.py -v`
Expected: FAIL — `ImportError: cannot import name 'validate_segments'`

- [ ] **Step 3: 实现**

在 `service/en_desktop/phonics.py` 末尾追加：

```python
def validate_segments(word: str, ipa: str, segments: list) -> bool:
    """
    校验 LLM 返回的拆分结果，全部满足才算通过：
    1. 所有 letters 依次拼接（忽略大小写）等于原词
    2. 所有 ipa 依次拼接（去装饰符号后）等于原始音标同样处理后的结果
    3. 每一段 ipa 都能被音素清单完整分词（不含清单外符号）
    """
    if not segments:
        return False
    try:
        letters_concat = "".join(seg["letters"] for seg in segments)
        ipa_concat = "".join(normalize_ipa(seg["ipa"]) for seg in segments)
    except (KeyError, TypeError):
        return False

    if letters_concat.lower() != (word or "").lower():
        return False
    if ipa_concat != normalize_ipa(ipa):
        return False
    return all(tokenize_ipa(seg["ipa"]) for seg in segments)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/bin/pytest tests/en_desktop/test_phonics.py -v`
Expected: PASS（9 passed）

- [ ] **Step 5: Commit**

```bash
git add service/en_desktop/phonics.py tests/en_desktop/test_phonics.py
git commit -m "feat: 新增拼读拆分结果校验"
```

---

### Task 4: DashScope LLM 调用封装

**Files:**
- Create: `service/en_desktop/phonics_llm.py`
- Test: `tests/en_desktop/test_phonics_llm.py`

**Interfaces:**
- Produces: `request_phonics_segments(word: str, ipa: str) -> list | None` —— Task 5 的生成脚本调用它拿 LLM 返回的 segments（未校验，校验交给 Task 3 的 `validate_segments`）

- [ ] **Step 1: 写失败测试**

```python
# tests/en_desktop/test_phonics_llm.py
"""
DashScope LLM 调用封装测试：mock requests.post，不打真实网络请求
"""
import json

import pytest

from service.en_desktop import phonics_llm


class _FakeResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def _llm_json_response(segments):
    return _FakeResponse(
        200,
        {"choices": [{"message": {"content": json.dumps({"segments": segments})}}]},
    )


def test_request_phonics_segments_success(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    segments = [{"letters": "c", "ipa": "k"}, {"letters": "at", "ipa": "æt"}]
    monkeypatch.setattr(
        phonics_llm.requests, "post", lambda *a, **kw: _llm_json_response(segments)
    )

    result = phonics_llm.request_phonics_segments("cat", "/kæt/")
    assert result == segments


def test_request_phonics_segments_http_error(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(
        phonics_llm.requests, "post", lambda *a, **kw: _FakeResponse(500, {})
    )

    assert phonics_llm.request_phonics_segments("cat", "/kæt/") is None


def test_request_phonics_segments_bad_json_content(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    bad_response = _FakeResponse(200, {"choices": [{"message": {"content": "not json"}}]})
    monkeypatch.setattr(phonics_llm.requests, "post", lambda *a, **kw: bad_response)

    assert phonics_llm.request_phonics_segments("cat", "/kæt/") is None


def test_request_phonics_segments_missing_api_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        phonics_llm.request_phonics_segments("cat", "/kæt/")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/bin/pytest tests/en_desktop/test_phonics_llm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'service.en_desktop.phonics_llm'`

- [ ] **Step 3: 实现**

```python
# service/en_desktop/phonics_llm.py
"""
调用 DashScope（阿里百炼）OpenAI 兼容接口，让 LLM 给出单词的字母段-音素拆分。
只负责拿到 LLM 的原始 segments，不做校验——校验交给 service/en_desktop/phonics.py 的 validate_segments。
"""
import json
import os

import requests

DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_MODEL = "qwen-plus"

_PROMPT_TEMPLATE = """你是英语自然拼读（phonics）教学专家。给定单词和它的 IPA 音标，
把单词拆成若干"字母段-音素"对应的片段，用于教学生逐段拼读。

单词：{word}
音标：{ipa}

要求：
1. 严格按音标里出现的音素顺序拆分，每个片段对应单词里连续的一个或多个字母
2. 所有片段的 letters 依次拼接必须完全等于单词本身（大小写不敏感）
3. 所有片段的 ipa 依次拼接必须完全等于给定音标去掉 / ˈ ˌ . 和空格后的结果
4. 只返回 JSON，不要任何解释文字，格式：{{"segments": [{{"letters": "...", "ipa": "..."}}]}}
"""


def request_phonics_segments(word: str, ipa: str) -> list | None:
    """
    调用 LLM 返回 segments 列表（未校验）。
    HTTP 失败或返回内容解析不出合法 JSON 时返回 None，由调用方决定跳过。
    DASHSCOPE_API_KEY 未配置时直接抛错——这是部署问题，不是单个词的问题，不该被吞掉。
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")

    payload = {
        "model": DASHSCOPE_MODEL,
        "messages": [{"role": "user", "content": _PROMPT_TEMPLATE.format(word=word, ipa=ipa)}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    resp = requests.post(
        DASHSCOPE_CHAT_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        return None

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)["segments"]
    except (KeyError, IndexError, ValueError, TypeError):
        return None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/bin/pytest tests/en_desktop/test_phonics_llm.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add service/en_desktop/phonics_llm.py tests/en_desktop/test_phonics_llm.py
git commit -m "feat: 新增 DashScope 拼读拆分 LLM 调用封装"
```

---

### Task 5: 生成脚本

**Files:**
- Create: `scripts/generate_phonics.py`
- Modify: `.env.example`

**Interfaces:**
- Consumes: `EnDesktopWord`、`EnDesktopWordPhonics`（Task 1）、`validate_segments`（Task 3）、`request_phonics_segments`（Task 4）
- Produces: 无（脚本，本身不被其他代码 import）

这一步是胶水脚本，仓库里现有的 `scripts/import_ecdict.py`/`scripts/rebuild_roots_affixes.py` 也都没有自动化测试覆盖——脚本本身用 Task 6 的小样本试跑来验证，不额外写单测。

- [ ] **Step 1: `.env.example` 加一行**

在 `.env.example` 里，靠近其他 key 的位置追加：

```
# 拼读拆分生成脚本（scripts/generate_phonics.py）用，阿里百炼 DashScope API Key
DASHSCOPE_API_KEY=
```

- [ ] **Step 2: 写脚本**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_phonics.py .env.example
git commit -m "feat: 新增拼读拆分生成脚本 generate_phonics.py"
```

---

### Task 6: 小样本试跑与人工验证

**Files:** 无代码改动，纯手动执行验证

- [ ] **Step 1: 配置 API Key**

在本地 `.env`（不提交）里加一行真实的 `DASHSCOPE_API_KEY=<你的百炼 key>`。

- [ ] **Step 2: dry-run 小样本，先看质量**

```bash
.venv/bin/python scripts/generate_phonics.py --limit 20
```

Expected: 打印 20 个词的 `[DRY-RUN] word ipa -> segments`，人工检查拆分是否合理（重点看 `school`/`knight`/`though` 这类拼写不规则的词，如果词库里有的话）。如果失败/跳过比例明显偏高，回到 Task 4 调整 prompt 或 Task 2 补充音素清单，再重新跑这一步。

- [ ] **Step 3: 确认质量后写库**

```bash
.venv/bin/python scripts/generate_phonics.py --limit 20 --apply
```

Expected: 打印 `[APPLY]` 而不是 `[DRY-RUN]`，末尾统计成功数量。

- [ ] **Step 4: 手动查库确认**

```bash
mysql -h localhost -u root -p english_new -e "SELECT word_id, segments FROM word_phonics LIMIT 20;"
```

Expected: 能看到 20 条记录，`segments` 是格式正确的 JSON 数组。

- [ ] **Step 5: 视质量决定是否放开跑全量**

样本质量满意后，再决定是否去掉 `--limit` 跑全量（跑之前注意 DashScope 的调用量级和费用，词库有几千词时建议分批跑，比如每次 `--limit 500` 观察一下失败率）。这一步不写进本计划的自动化范围，由你根据实际样本结果决定。

## Self-Review

- **Spec 覆盖**：本计划覆盖了 en-elctron 设计文档里"一、后端数据模型"和"二、生成脚本"两节的全部内容（表结构、硬校验规则、`--dry-run`/`--apply`、增量支持、日志不重试）。"三、API 扩展"和"四/五"前端部分不在本计划范围内，按你的要求留到下一个计划。
- **占位符检查**：所有代码块都是完整实现，没有 TBD/TODO。
- **类型一致性**：`EnDesktopWordPhonics.segments` / `validate_segments(segments: list)` / `request_phonics_segments(...) -> list | None` 三处的 `segments` 都是同一种结构 `[{"letters": str, "ipa": str}, ...]`，没有命名或类型不一致的地方。
