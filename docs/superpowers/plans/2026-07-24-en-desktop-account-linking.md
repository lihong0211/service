# en-desktop 小程序个人资料 + 桌面账号打通 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 小程序"我的"页展示/编辑真实头像昵称，并能把小程序的匿名微信身份和桌面端账号密码
账号合并成同一条用户记录。

**Architecture:** 后端（`service-ali`，FastAPI + SQLAlchemy）在 `service/en_desktop/auth.py`
新增 `update_profile`/`set_credentials`/`bind_account` 三个服务函数和一个新文件
`service/en_desktop/avatar.py`，`bind_account` 的词库/收藏迁移逻辑单独放
`service/en_desktop/account_merge.py`（纯 DB 操作，不签发 token，可独立测试）。前端
（`en-mini`，uni-app/Vue2）改 `pages/my/my.vue` 加个人资料卡片和账号绑定入口，`common/
requestDesktop.js` 加两个 token 读写的辅助导出。

**Tech Stack:** 后端 FastAPI 0.115 + SQLAlchemy（现有 `EnDesktopModel` CRUD 约定）+ bcrypt；
前端 uni-app（微信小程序 `chooseAvatar`/`type="nickname"` 官方组件）。

## Global Constraints

- 所有新路由响应统一 `{"code": 200/400/401/500, "msg": ..., "data": ...}`，用
  `routes/en_desktop.py` 现有的 `_json_200()` 包装，不用 `app.response.api_response`
  （小程序/桌面端客户端约定按 body 里的 `code` 字段判断，不看 HTTP 状态码）。
- 密码哈希/校验只能走 `service/en_desktop/security.py` 的 `hash_password`/`verify_password`。
- 服务函数的异常分支统一 `except Exception as e: return unexpected_error_response(e, db.session)`。
- 表操作只用 `EnDesktopModel` 的 `insert`/`update`/`select_by`/`select_one_by`/`get_by_id`/
  `delete`/`delete_by`，或直接对已取出的 ORM 对象赋值属性再 `db.session.commit()`（后者是
  `libraries.py` 里 `favorite_library()` 已用的写法）——**不要**用 `EnDesktopModel.update()`
  去清空字段，它会跳过 `None` 值，清空必须走对象属性直接赋值。
- `db.session` 的 `autoflush=False`（见 `app/database.py`）：涉及"先改一条记录、再按旧值做
  批量条件更新"的地方，必须显式 `db.session.flush()`，否则批量更新会读到未落库的旧数据。
- 新增依赖需要写进 `requirements.txt`（版本号取当前已安装版本）。
- 前端沿用 `common/notebook-theme.css` 的 CSS 变量（`--paper`/`--ink`/`--ink-soft`/
  `--margin`/`--highlight`），不要引入新配色。
- 项目没有 Vue 组件单元测试基建（`package.json` 的 `test` 脚本是占位符），前端改动用微信
  开发者工具手动验证，不用新增自动化测试。

---

## Backend — `service-ali`

### Task 1: 声明 `python-multipart` 依赖

头像上传要用 FastAPI 的 `UploadFile`，这需要 `python-multipart` 解析 multipart 请求体。
当前环境已经装了这个包（大概率是别的依赖间接带进来的），但 `requirements.txt` 里没有显式
声明，补上避免部署到新环境时炸掉。

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 确认已安装版本**

Run: `pip show python-multipart | grep Version`
Expected: `Version: 0.0.20`（如果输出的版本不同，用实际输出的版本号替换下面 Step 2 里的
`0.0.20`）

- [ ] **Step 2: 在 `requirements.txt` 里 `fastapi==0.115.6` 那一行下面加一行**

```
fastapi==0.115.6
python-multipart==0.0.20
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: 声明 python-multipart 依赖（头像上传要用）"
```

---

### Task 2: `auth.py` 新增 `update_profile`（改昵称）+ 路由

**Files:**
- Modify: `service/en_desktop/auth.py`
- Modify: `routes/en_desktop.py`
- Test: `tests/en_desktop/test_auth.py`

**Interfaces:**
- Produces: `auth.update_profile(user_id: int, data: dict) -> dict`，返回
  `{"code": 200, "msg": "success", "data": <EnDesktopUser.public_dict()>}`，昵称非法时
  `{"code": 400, "msg": str}`。

- [ ] **Step 1: 在 `tests/en_desktop/test_auth.py` 末尾追加失败的测试**

```python
def test_update_profile_success(en_desktop_db):
    result = auth.register({"username": "alice", "password": "secret"})
    user_id = result["data"]["user"]["id"]

    updated = auth.update_profile(user_id, {"nickname": "新昵称"})
    assert updated["code"] == 200
    assert updated["data"]["nickname"] == "新昵称"


def test_update_profile_validates_length(en_desktop_db):
    result = auth.register({"username": "alice", "password": "secret"})
    user_id = result["data"]["user"]["id"]

    assert auth.update_profile(user_id, {"nickname": ""})["code"] == 400
    assert auth.update_profile(user_id, {"nickname": "a" * 51})["code"] == 400
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/en_desktop/test_auth.py -k update_profile -v`
Expected: `FAIL` — `AttributeError: module 'service.en_desktop.auth' has no attribute
'update_profile'`

- [ ] **Step 3: 在 `service/en_desktop/auth.py` 的 `me()` 函数后面加**

```python
def update_profile(user_id: int, data: dict) -> dict:
    """更新当前用户昵称"""
    nickname = (data.get("nickname") or "").strip()
    if not 1 <= len(nickname) <= 50:
        return {"code": 400, "msg": "昵称长度需在1-50个字符"}

    try:
        EnDesktopUser.update({"id": user_id, "nickname": nickname})
        return {"code": 200, "msg": "success", "data": EnDesktopUser.get_by_id(user_id).public_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/en_desktop/test_auth.py -k update_profile -v`
Expected: `2 passed`

- [ ] **Step 5: 在 `routes/en_desktop.py` 的 `route_auth_me` 后面加路由**

```python
@router.post("/auth/profile")
async def route_auth_profile(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(auth_service.update_profile(user_id, await _body(request)))
```

- [ ] **Step 6: Commit**

```bash
git add service/en_desktop/auth.py routes/en_desktop.py tests/en_desktop/test_auth.py
git commit -m "feat(en-desktop): 新增 /auth/profile 更新昵称接口"
```

---

### Task 3: `service/en_desktop/avatar.py`（头像上传）+ 路由

**Files:**
- Create: `service/en_desktop/avatar.py`
- Modify: `routes/en_desktop.py`
- Test: `tests/en_desktop/test_avatar.py`

**Interfaces:**
- Produces: `avatar.save_avatar(user_id: int, content: bytes) -> dict`，返回
  `{"code": 200, "msg": "success", "data": <EnDesktopUser.public_dict()>}`，`data["avatar"]`
  是拼好的公网 URL。

- [ ] **Step 1: 创建 `tests/en_desktop/test_avatar.py`**

```python
"""
头像保存测试：STATIC_DIR/PUBLIC_BASE_URL 走环境变量注入，测试里用 monkeypatch 指到
tmp_path，跟 sentences.py 音频文件的测试思路一致——不依赖真实服务器磁盘路径。
"""
import os

from model.en_desktop import EnDesktopUser
from service.en_desktop import auth, avatar


def test_save_avatar_writes_file_and_updates_user(en_desktop_db, tmp_path, monkeypatch):
    monkeypatch.setattr(avatar, "STATIC_DIR", str(tmp_path))
    monkeypatch.setattr(avatar, "PUBLIC_BASE_URL", "https://x.test/avatars")

    result = auth.register({"username": "alice", "password": "secret"})
    user_id = result["data"]["user"]["id"]

    saved = avatar.save_avatar(user_id, b"fake-jpg-bytes")
    assert saved["code"] == 200
    avatar_url = saved["data"]["avatar"]
    assert avatar_url.startswith("https://x.test/avatars/")

    filename = avatar_url.rsplit("/", 1)[-1]
    assert filename.startswith(f"{user_id}_")
    assert os.path.exists(os.path.join(str(tmp_path), filename))

    user = EnDesktopUser.get_by_id(user_id)
    assert user.avatar == avatar_url
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/en_desktop/test_avatar.py -v`
Expected: `FAIL` — `ModuleNotFoundError: No module named 'service.en_desktop.avatar'`

- [ ] **Step 3: 创建 `service/en_desktop/avatar.py`**

```python
# service/en_desktop/avatar.py
"""
en-desktop 用户头像：小程序 chooseAvatar 选取后的临时文件在这里落盘。
跟 sentences.py 的例句音频一样，存本地 static 目录 + 拼公网 URL，同一套环境变量风格，
不引入新的对象存储依赖。
"""
import os
import uuid

from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import EnDesktopUser

STATIC_DIR = os.environ.get("AVATAR_STATIC_DIR", "/lihong/static/en_desktop_avatars")
PUBLIC_BASE_URL = os.environ.get(
    "AVATAR_PUBLIC_BASE_URL", "https://doctor-dog.com/static/en_desktop_avatars"
)


def save_avatar(user_id: int, content: bytes) -> dict:
    try:
        os.makedirs(STATIC_DIR, exist_ok=True)
        filename = f"{user_id}_{uuid.uuid4().hex}.jpg"
        with open(os.path.join(STATIC_DIR, filename), "wb") as f:
            f.write(content)

        avatar_url = f"{PUBLIC_BASE_URL}/{filename}"
        EnDesktopUser.update({"id": user_id, "avatar": avatar_url})
        return {
            "code": 200,
            "msg": "success",
            "data": EnDesktopUser.get_by_id(user_id).public_dict(),
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/en_desktop/test_avatar.py -v`
Expected: `1 passed`

- [ ] **Step 5: 在 `routes/en_desktop.py` 顶部 import 区加**

```python
from service.en_desktop import avatar as avatar_service
```

（放在 `from service.en_desktop import auth as auth_service` 后面一行，保持字母序）

- [ ] **Step 6: 在 `route_auth_profile` 后面加路由，并给文件头部的 `fastapi` import 加
  `File`/`UploadFile`**

把文件顶部这一行：
```python
from fastapi import APIRouter, BackgroundTasks, Header, Query, Request
```
改成：
```python
from fastapi import APIRouter, BackgroundTasks, File, Header, Query, Request, UploadFile
```

加路由：
```python
@router.post("/auth/avatar")
async def route_auth_avatar(
    file: UploadFile = File(...), authorization: str | None = Header(None)
):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    content = await file.read()
    return _json_200(avatar_service.save_avatar(user_id, content))
```

- [ ] **Step 7: Commit**

```bash
git add service/en_desktop/avatar.py routes/en_desktop.py tests/en_desktop/test_avatar.py
git commit -m "feat(en-desktop): 新增 /auth/avatar 头像上传接口"
```

---

### Task 4: `auth.py` 新增 `set_credentials`（认领当前账号）+ 路由

**Files:**
- Modify: `service/en_desktop/auth.py`
- Modify: `routes/en_desktop.py`
- Test: `tests/en_desktop/test_auth.py`

**Interfaces:**
- Produces: `auth.set_credentials(user_id: int, data: dict) -> dict`，成功返回
  `{"code": 200, "msg": "success", "data": <EnDesktopUser.public_dict()>}`。

- [ ] **Step 1: 在 `tests/en_desktop/test_auth.py` 末尾追加失败的测试**

```python
def test_set_credentials_success(en_desktop_db, monkeypatch):
    monkeypatch.setattr(auth.wechat_oauth, "exchange_code_for_mini_openid", lambda code: "mini-openid-1")
    mini = auth.mini_login({"code": "any"})
    user_id = mini["data"]["user"]["id"]

    result = auth.set_credentials(user_id, {"username": "bob", "password": "secret"})
    assert result["code"] == 200
    assert result["data"]["username"] == "bob"
    assert result["data"]["wx_mini"] == "mini-openid-1"


def test_set_credentials_rejects_duplicate_username(en_desktop_db, monkeypatch):
    auth.register({"username": "bob", "password": "secret"})
    monkeypatch.setattr(auth.wechat_oauth, "exchange_code_for_mini_openid", lambda code: "mini-openid-1")
    mini = auth.mini_login({"code": "any"})
    user_id = mini["data"]["user"]["id"]

    result = auth.set_credentials(user_id, {"username": "bob", "password": "other"})
    assert result["code"] == 400


def test_set_credentials_rejects_when_already_set(en_desktop_db):
    result = auth.register({"username": "alice", "password": "secret"})
    user_id = result["data"]["user"]["id"]

    result = auth.set_credentials(user_id, {"username": "new-name", "password": "secret2"})
    assert result["code"] == 400
    assert "已设置" in result["msg"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/en_desktop/test_auth.py -k set_credentials -v`
Expected: `FAIL` — `AttributeError: module 'service.en_desktop.auth' has no attribute
'set_credentials'`

- [ ] **Step 3: 在 `service/en_desktop/auth.py` 的 `update_profile()` 后面加**

```python
def set_credentials(user_id: int, data: dict) -> dict:
    """给当前（一般是匿名 wx_mini）账号直接设置用户名密码，不新建行、不改 token。
    仅当当前账号还没有 username 时可用——已经设置过就必须走 bind_account 合并。"""
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not 1 <= len(username) <= 20:
        return {"code": 400, "msg": "用户名长度需在1-20个字符"}
    if not 3 <= len(password) <= 100:
        return {"code": 400, "msg": "密码长度需在3-100个字符"}

    try:
        user = EnDesktopUser.get_by_id(user_id)
        if user.username:
            return {"code": 400, "msg": "当前账号已设置用户名"}
        if EnDesktopUser.select_one_by({"username": username}):
            return {"code": 400, "msg": "用户名已存在"}

        EnDesktopUser.update(
            {"id": user_id, "username": username, "password": hash_password(password)}
        )
        return {"code": 200, "msg": "success", "data": EnDesktopUser.get_by_id(user_id).public_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/en_desktop/test_auth.py -k set_credentials -v`
Expected: `3 passed`

- [ ] **Step 5: 在 `routes/en_desktop.py` 的 `route_auth_avatar` 后面加路由**

```python
@router.post("/auth/set-credentials")
async def route_auth_set_credentials(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(auth_service.set_credentials(user_id, await _body(request)))
```

- [ ] **Step 6: Commit**

```bash
git add service/en_desktop/auth.py routes/en_desktop.py tests/en_desktop/test_auth.py
git commit -m "feat(en-desktop): 新增 /auth/set-credentials 认领账号接口"
```

---

### Task 5: `service/en_desktop/account_merge.py`（词库/收藏合并逻辑）

这是 `bind_account` 用的纯 DB 合并逻辑，单独拆文件方便独立测试，不涉及 token/wx_mini（那部分
留给 Task 6 的 `bind_account`）。

**Files:**
- Create: `service/en_desktop/account_merge.py`
- Test: `tests/en_desktop/test_account_merge.py`

**Interfaces:**
- Produces: `account_merge.merge_libraries_and_favorites(source_user_id: int, target_user_id:
  int) -> None`。不提交事务（调用方统一 `db.session.commit()`），只挂起 ORM 对象的属性修改
  和 `EnDesktopWordLibrary.delete(..., commit=False)`/`EnDesktopWordLibraryItem.delete_by(...)`
  这类已有的软删除调用。

- [ ] **Step 1: 创建 `tests/en_desktop/test_account_merge.py`**

```python
"""
account_merge 合并逻辑测试：默认词库合并去重、自建库同名改名过户、收藏去重。
"""
from app.database import db
from model.en_desktop import (
    EnDesktopWordLibrary,
    EnDesktopWordLibraryFavorite,
    EnDesktopWordLibraryItem,
)
from service.en_desktop import account_merge, libraries
from service.en_desktop.libraries import DEFAULT_LIBRARY_NAME


def _make_word(word_text: str):
    from model.en_desktop import EnDesktopWord

    return EnDesktopWord.insert({"word": word_text})


def test_merge_default_library_dedupes_items(en_desktop_db):
    source_lib = libraries.ensure_default_library(1)
    target_lib = libraries.ensure_default_library(2)

    shared_word = _make_word("apple")
    source_only_word = _make_word("banana")
    EnDesktopWordLibraryItem.insert({"word_library_id": source_lib.id, "word_id": shared_word})
    EnDesktopWordLibraryItem.insert({"word_library_id": source_lib.id, "word_id": source_only_word})
    EnDesktopWordLibraryItem.insert({"word_library_id": target_lib.id, "word_id": shared_word})

    account_merge.merge_libraries_and_favorites(source_user_id=1, target_user_id=2)
    db.session.commit()

    remaining_target_items = EnDesktopWordLibraryItem.select_by({"word_library_id": target_lib.id})
    assert {i.word_id for i in remaining_target_items} == {shared_word, source_only_word}
    # source 的默认库被软删
    assert EnDesktopWordLibrary.get_by_id(source_lib.id) is None


def test_merge_renames_conflicting_custom_library(en_desktop_db):
    source_lib_id = EnDesktopWordLibrary.insert({"user_id": 1, "name": "我的词库"})
    target_lib_id = EnDesktopWordLibrary.insert({"user_id": 2, "name": "我的词库"})

    account_merge.merge_libraries_and_favorites(source_user_id=1, target_user_id=2)
    db.session.commit()

    target_libs = EnDesktopWordLibrary.select_by({"user_id": 2})
    names = {lib.name for lib in target_libs}
    assert "我的词库" in names
    assert "我的词库（微信）" in names
    assert EnDesktopWordLibrary.get_by_id(source_lib_id).user_id == 2


def test_merge_transfers_non_conflicting_library(en_desktop_db):
    source_lib_id = EnDesktopWordLibrary.insert({"user_id": 1, "name": "自建库A"})

    account_merge.merge_libraries_and_favorites(source_user_id=1, target_user_id=2)
    db.session.commit()

    lib = EnDesktopWordLibrary.get_by_id(source_lib_id)
    assert lib.user_id == 2
    assert lib.name == "自建库A"


def test_merge_favorites_dedupes(en_desktop_db):
    public_lib_id = EnDesktopWordLibrary.insert({"user_id": 99, "name": "公共库", "is_public": 1})
    other_public_lib_id = EnDesktopWordLibrary.insert(
        {"user_id": 99, "name": "公共库2", "is_public": 1}
    )
    db.session.add(EnDesktopWordLibraryFavorite(user_id=1, word_library_id=public_lib_id))
    db.session.add(EnDesktopWordLibraryFavorite(user_id=2, word_library_id=public_lib_id))
    db.session.add(EnDesktopWordLibraryFavorite(user_id=1, word_library_id=other_public_lib_id))
    db.session.commit()

    account_merge.merge_libraries_and_favorites(source_user_id=1, target_user_id=2)
    db.session.commit()

    target_favorites = EnDesktopWordLibraryFavorite.select_by({"user_id": 2})
    assert {f.word_library_id for f in target_favorites} == {public_lib_id, other_public_lib_id}
    source_favorites = EnDesktopWordLibraryFavorite.select_by({"user_id": 1})
    assert source_favorites == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/en_desktop/test_account_merge.py -v`
Expected: `FAIL` — `ModuleNotFoundError: No module named 'service.en_desktop.account_merge'`

- [ ] **Step 3: 创建 `service/en_desktop/account_merge.py`**

```python
# service/en_desktop/account_merge.py
"""
账号合并：把 source_user 名下的词库和收藏迁移到 target_user，服务于 auth.bind_account。
只挂起 ORM 对象修改，不提交事务——commit 由调用方统一做（bind_account 里还要处理
wx_mini 过户和 flush 顺序，两者必须在同一个事务里）。

全程直接修改已取出的 ORM 对象属性（不用 EnDesktopModel.update()，那个方法会跳过 None
值，也不适合按名称查重后再改这种场景），跟 libraries.py 的 favorite_library() 是同一种
写法。
"""
from datetime import datetime

from app.database import db
from model.en_desktop import (
    EnDesktopWordLibrary,
    EnDesktopWordLibraryFavorite,
    EnDesktopWordLibraryItem,
)
from service.en_desktop.libraries import PROTECTED_LIBRARY_NAMES


def _merge_library_items(source_lib_id: int, target_lib_id: int) -> None:
    """source 默认词库的单词并入 target 同名默认词库：target 已有的对应 item 直接软删
    source 那条，没有的把 word_library_id 过户过去。"""
    target_word_ids = {
        row[0]
        for row in db.session.query(EnDesktopWordLibraryItem.word_id)
        .where(
            EnDesktopWordLibraryItem.word_library_id == target_lib_id,
            EnDesktopWordLibraryItem.deleted_at.is_(None),
        )
        .all()
    }
    source_items = (
        db.session.query(EnDesktopWordLibraryItem)
        .where(
            EnDesktopWordLibraryItem.word_library_id == source_lib_id,
            EnDesktopWordLibraryItem.deleted_at.is_(None),
        )
        .all()
    )
    for item in source_items:
        if item.word_id in target_word_ids:
            item.deleted_at = datetime.now()
        else:
            item.word_library_id = target_lib_id
            target_word_ids.add(item.word_id)


def merge_libraries_and_favorites(source_user_id: int, target_user_id: int) -> None:
    source_libs = EnDesktopWordLibrary.select_by({"user_id": source_user_id})
    target_libs_by_name = {
        lib.name: lib for lib in EnDesktopWordLibrary.select_by({"user_id": target_user_id})
    }

    for lib in source_libs:
        conflict = target_libs_by_name.get(lib.name)
        if conflict and lib.name in PROTECTED_LIBRARY_NAMES:
            # 默认词库（生词本/复习本）两边都有：词条合并进 target 的那份，source 这份删掉
            _merge_library_items(lib.id, conflict.id)
            EnDesktopWordLibrary.delete(lib.id, commit=False)
        elif conflict:
            # 自建词库同名冲突：改名后再过户，避免撞 (user_id, name) 唯一约束
            lib.name = f"{lib.name}（微信）"
            lib.user_id = target_user_id
        else:
            lib.user_id = target_user_id

    target_favorite_lib_ids = {
        row[0]
        for row in db.session.query(EnDesktopWordLibraryFavorite.word_library_id)
        .where(EnDesktopWordLibraryFavorite.user_id == target_user_id)
        .all()
    }
    for fav in EnDesktopWordLibraryFavorite.select_by({"user_id": source_user_id}):
        if fav.word_library_id in target_favorite_lib_ids:
            fav.deleted_at = datetime.now()
        else:
            fav.user_id = target_user_id
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/en_desktop/test_account_merge.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add service/en_desktop/account_merge.py tests/en_desktop/test_account_merge.py
git commit -m "feat(en-desktop): 新增账号合并的词库/收藏迁移逻辑"
```

---

### Task 6: `auth.py` 新增 `bind_account`（合并进已有桌面账号）+ 路由

**Files:**
- Modify: `service/en_desktop/auth.py`
- Modify: `routes/en_desktop.py`
- Test: `tests/en_desktop/test_auth.py`

**Interfaces:**
- Consumes: `account_merge.merge_libraries_and_favorites(source_user_id: int,
  target_user_id: int) -> None`（Task 5）
- Produces: `auth.bind_account(user_id: int, data: dict) -> dict`，成功返回
  `{"code": 200, "msg": "success", "data": {"token": str, "user": <public_dict>}}`。

- [ ] **Step 1: 在 `tests/en_desktop/test_auth.py` 末尾追加失败的测试**

```python
def test_bind_account_merges_and_transfers_wx_mini(en_desktop_db, monkeypatch):
    target = auth.register({"username": "alice", "password": "secret"})
    target_id = target["data"]["user"]["id"]

    monkeypatch.setattr(auth.wechat_oauth, "exchange_code_for_mini_openid", lambda code: "mini-openid-1")
    mini = auth.mini_login({"code": "any"})
    source_id = mini["data"]["user"]["id"]

    EnDesktopWordLibrary.insert({"user_id": source_id, "name": "自建库A"})

    result = auth.bind_account(source_id, {"username": "alice", "password": "secret"})
    assert result["code"] == 200
    assert result["data"]["user"]["id"] == target_id
    assert result["data"]["user"]["wx_mini"] == "mini-openid-1"
    new_token = result["data"]["token"]

    # 源记录已被软删
    assert EnDesktopUser.get_by_id(source_id) is None
    # 词库已过户
    lib = EnDesktopWordLibrary.select_one_by({"user_id": target_id, "name": "自建库A"})
    assert lib is not None

    # 之后不管是这个新 token，还是重新静默登录，解析到的都是合并后的 target 账号
    assert auth.me(new_token)["code"] == 200
    assert auth.me(new_token)["data"]["id"] == target_id
    again = auth.mini_login({"code": "any"})
    assert again["data"]["user"]["id"] == target_id


def test_bind_account_wrong_password(en_desktop_db, monkeypatch):
    auth.register({"username": "alice", "password": "secret"})
    monkeypatch.setattr(auth.wechat_oauth, "exchange_code_for_mini_openid", lambda code: "mini-openid-1")
    mini = auth.mini_login({"code": "any"})
    source_id = mini["data"]["user"]["id"]

    result = auth.bind_account(source_id, {"username": "alice", "password": "wrong"})
    assert result["code"] == 400


def test_bind_account_rejects_self(en_desktop_db):
    result = auth.register({"username": "alice", "password": "secret"})
    user_id = result["data"]["user"]["id"]

    result = auth.bind_account(user_id, {"username": "alice", "password": "secret"})
    assert result["code"] == 400
```

在文件顶部 import 区加上这两个（如果还没有）：
```python
from model.en_desktop import EnDesktopUser, EnDesktopWordLibrary
```
（`EnDesktopUser` 应该已经 import 过了，只需要确认加上 `EnDesktopWordLibrary`）

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/en_desktop/test_auth.py -k bind_account -v`
Expected: `FAIL` — `AttributeError: module 'service.en_desktop.auth' has no attribute
'bind_account'`

- [ ] **Step 3: 在 `service/en_desktop/auth.py` 顶部 import 区加**

```python
from service.en_desktop import account_merge
```

- [ ] **Step 4: 在 `set_credentials()` 后面加 `bind_account`**

```python
def bind_account(user_id: int, data: dict) -> dict:
    """把当前（一般是匿名 wx_mini）账号合并进已有的账号密码账号：迁移词库/收藏，
    wx_mini 过户给目标账号，源记录软删。合并后无论静默登录还是重新登录，wx_mini
    都指向目标账号，天然是同一个身份，requestDesktop.js/mini_login/me 都不用改。"""
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return {"code": 400, "msg": "请输入用户名和密码"}

    try:
        target = EnDesktopUser.select_one_by({"username": username})
        if not target or not target.password or not verify_password(password, target.password):
            return {"code": 400, "msg": "用户名或密码错误"}
        if target.id == user_id:
            return {"code": 400, "msg": "不能绑定自己"}

        source = EnDesktopUser.get_by_id(user_id)
        account_merge.merge_libraries_and_favorites(source.id, target.id)

        # 必须先清空 source.wx_mini 并 flush，再给 target 赋值——wx_mini 有唯一索引，
        # autoflush=False 不会在两条 UPDATE 之间自动排序，反过来做会在 flush 时撞唯一约束
        source_wx_mini = source.wx_mini
        source.wx_mini = None
        db.session.flush()
        target.wx_mini = source_wx_mini

        EnDesktopUser.delete(source.id, commit=False)
        db.session.commit()

        return _auth_success(target.id)
    except Exception as e:
        return unexpected_error_response(e, db.session)
```

- [ ] **Step 5: 跑测试确认通过**

Run: `pytest tests/en_desktop/test_auth.py -k bind_account -v`
Expected: `3 passed`

- [ ] **Step 6: 跑全部 en_desktop 测试确认没有破坏既有用例**

Run: `pytest tests/en_desktop/ -v`
Expected: 全部 `PASS`

- [ ] **Step 7: 在 `routes/en_desktop.py` 的 `route_auth_set_credentials` 后面加路由**

```python
@router.post("/auth/bind-account")
async def route_auth_bind_account(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(auth_service.bind_account(user_id, await _body(request)))
```

- [ ] **Step 8: Commit**

```bash
git add service/en_desktop/auth.py routes/en_desktop.py tests/en_desktop/test_auth.py
git commit -m "feat(en-desktop): 新增 /auth/bind-account 合并已有桌面账号接口"
```

---

## Frontend — `en-mini`

### Task 7: `requestDesktop.js` 导出 `getToken`/`setToken`

`bind-account` 成功后拿到的新 token 要覆盖本地存储；头像上传走 `uni.uploadFile`（不能走
现有的 JSON-only `request()` 封装），需要单独读 token 拼 header。两处都需要访问
`TOKEN_KEY` 这个模块内部常量，导出两个小函数比在别处硬编码 `'en_desktop_token'` 字符串好。

**Files:**
- Modify: `common/requestDesktop.js`

**Interfaces:**
- Produces: `getToken(): string`, `setToken(token: string): void`（具名导出，和现有的
  `export default async function request(...)` 共存）

- [ ] **Step 1: 在 `const TOKEN_KEY = "en_desktop_token";` 后面加**

```js
export function getToken() {
	return uni.getStorageSync(TOKEN_KEY);
}

export function setToken(token) {
	uni.setStorageSync(TOKEN_KEY, token);
}
```

- [ ] **Step 2: 手动验证没有破坏原有默认导出**

Run: `node -e "require('@babel/core')" 2>/dev/null; grep -c 'export' common/requestDesktop.js`
Expected: 输出 `3`（`export default async function request` + 新增的两个 `export function`）

- [ ] **Step 3: Commit**

```bash
git add common/requestDesktop.js
git commit -m "feat: requestDesktop.js 导出 getToken/setToken"
```

---

### Task 8: `my.vue` 个人资料卡片（头像 + 昵称展示/编辑）

**Files:**
- Modify: `pages/my/my.vue`

**Interfaces:**
- Consumes: `request({url, method, data})`（现有默认导出）, `getToken()`（Task 7）

- [ ] **Step 1: 把 `pages/my/my.vue` 的 `<script>` 整段替换成**

```html
<script>
import request from '~@/common/requestDesktop'
import { getToken } from '~@/common/requestDesktop'
import { apiHost } from '~@/common/env'
import { getNavBarInfo } from '~@/common/util'
import bgImage from '~@/common/bg-image.vue'

export default {
	components: { bgImage },
	data() {
		return {
			ownLibraries: [],
			favoriteLibraries: [],
			safeTop: 0,
			user: null,
			editingNickname: false,
			nicknameDraft: ''
		};
	},
	onShow() {
		this.safeTop = getNavBarInfo().top
		this.getProfile()
		this.getLibraries()
	},
	methods: {
		getProfile() {
			request({
				url: 'auth/me',
				method: 'GET'
			}).then((data) => {
				this.user = data
			}).catch(() => {})
		},
		getLibraries() {
			request({
				url: 'libraries/list',
				method: 'GET'
			}).then((data) => {
				this.ownLibraries = data
			}).catch(() => {})

			request({
				url: 'libraries/favorites',
				method: 'GET'
			}).then((data) => {
				this.favoriteLibraries = data
			}).catch(() => {})
		},
		openLibrary(lib) {
			uni.navigateTo({
				url: `/pages/library-detail/library-detail?id=${lib.id}&name=${encodeURIComponent(lib.name)}`
			});
		},
		onChooseAvatar(e) {
			const filePath = e.detail.avatarUrl
			if (!filePath) return
			uni.uploadFile({
				url: apiHost + '/en-desktop/auth/avatar',
				filePath,
				name: 'file',
				header: { Authorization: `Bearer ${getToken()}` },
				success: (res) => {
					const body = JSON.parse(res.data)
					if (body.code === 200) {
						this.user = body.data
					} else {
						uni.showToast({ title: body.msg || '头像上传失败', icon: 'none' })
					}
				},
				fail: () => {
					uni.showToast({ title: '头像上传失败', icon: 'none' })
				}
			})
		},
		startEditNickname() {
			this.nicknameDraft = this.user && this.user.nickname || ''
			this.editingNickname = true
		},
		onNicknameConfirm(e) {
			const nickname = (e.detail.value || '').trim()
			this.editingNickname = false
			if (!nickname || nickname === (this.user && this.user.nickname)) return
			request({
				url: 'auth/profile',
				data: { nickname }
			}).then((data) => {
				this.user = data
			}).catch(() => {})
		}
	}
}
</script>
```

- [ ] **Step 2: 把 `<template>` 里 `<bg-image />` 后面、第一个 `<view class="section"` 前面
  加个人资料卡片**

```html
<view class="profile-card" v-if="user">
	<!-- #ifdef MP-WEIXIN -->
	<button class="avatar-btn" open-type="chooseAvatar" @chooseavatar="onChooseAvatar">
		<image class="avatar" :src="user.avatar || '/static/my.png'" mode="aspectFill" />
	</button>
	<!-- #endif -->
	<!-- #ifndef MP-WEIXIN -->
	<image class="avatar" :src="user.avatar || '/static/my.png'" mode="aspectFill" />
	<!-- #endif -->

	<view class="nickname-area">
		<!-- #ifdef MP-WEIXIN -->
		<input
			v-if="editingNickname"
			class="nickname-input"
			type="nickname"
			:value="nicknameDraft"
			@blur="onNicknameConfirm"
			focus
		/>
		<!-- #endif -->
		<!-- #ifndef MP-WEIXIN -->
		<input
			v-if="editingNickname"
			class="nickname-input"
			:value="nicknameDraft"
			@blur="onNicknameConfirm"
			focus
		/>
		<!-- #endif -->
		<text v-if="!editingNickname" class="nickname" @click="startEditNickname">{{ user.nickname || '点击设置昵称' }}</text>
	</view>
</view>
```

- [ ] **Step 3: 在 `<style>` 里 `.section:first-child { margin-top: 0; }` 后面加**

```css
.profile-card {
	display: flex;
	align-items: center;
	margin: 0 16px;
	padding: 16px;
	background-color: var(--paper);
	border: 1px solid rgba(232, 121, 249, 0.25);
	box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
	border-radius: 6px;
}

.avatar-btn {
	padding: 0;
	margin: 0;
	background: none;
	border: none;
	line-height: 0;
}

.avatar-btn::after {
	border: none;
}

.avatar {
	width: 56px;
	height: 56px;
	border-radius: 50%;
	background-color: var(--paper-deep);
	flex-shrink: 0;
}

.nickname-area {
	margin-left: 14px;
	flex: 1;
}

.nickname {
	font-family: Georgia, "Times New Roman", serif;
	font-size: 17px;
	font-weight: 700;
	color: var(--ink);
}

.nickname-input {
	font-size: 17px;
	color: var(--ink);
	border-bottom: 1px solid var(--rule);
	padding-bottom: 4px;
}
```

- [ ] **Step 4: 手动验证（微信开发者工具）**

在微信开发者工具里打开小程序项目，进"我的"页：
1. 确认页面顶部出现头像+昵称卡片，首次静默登录后昵称显示"微信用户"。
2. 点头像，走完官方头像选择流程后，确认头像立即更新成选的图。
3. 点昵称，输入框获得焦点并弹出微信昵称建议，输入后失焦，确认昵称文本更新。
4. 重新进小程序（下拉关闭再重新打开），确认头像昵称是刚才改的值（说明后端真的存住了）。

- [ ] **Step 5: Commit**

```bash
git add pages/my/my.vue
git commit -m "feat: 我的页新增个人资料卡片，支持头像昵称编辑"
```

---

### Task 9: `my.vue` 账号绑定入口（设置账号密码 / 绑定已有桌面账号）

**Files:**
- Modify: `pages/my/my.vue`

**Interfaces:**
- Consumes: `request({url, method, data})`, `setToken(token)`（Task 7）, `this.user`/
  `this.getProfile`/`this.getLibraries`（Task 8）

- [ ] **Step 1: `<script>` 的 import 那一行**

```js
import { getToken } from '~@/common/requestDesktop'
```
改成：
```js
import { getToken, setToken } from '~@/common/requestDesktop'
```

- [ ] **Step 2: `data()` 里加三个字段（跟 `nicknameDraft` 放一起）**

```js
credentialMode: null, // 'set' | 'bind' | null
credentialUsername: '',
credentialPassword: ''
```

- [ ] **Step 3: `methods` 里加**

```js
openCredentialForm(mode) {
	this.credentialMode = mode
	this.credentialUsername = ''
	this.credentialPassword = ''
},
closeCredentialForm() {
	this.credentialMode = null
},
submitCredentialForm() {
	const username = this.credentialUsername.trim()
	const password = this.credentialPassword
	if (!username || !password) {
		uni.showToast({ title: '请输入用户名和密码', icon: 'none' })
		return
	}
	const url = this.credentialMode === 'bind' ? 'auth/bind-account' : 'auth/set-credentials'
	request({ url, data: { username, password } }).then((data) => {
		this.credentialMode = null
		if (data.token) {
			setToken(data.token)
			this.user = data.user
			this.getLibraries()
		} else {
			this.user = data
		}
		uni.showToast({ title: '绑定成功', icon: 'success' })
	}).catch(() => {})
}
```

- [ ] **Step 4: `<template>` 在个人资料卡片 (`</view>` 结尾，即上一任务加的 `.profile-card`
  整块) 后面加账号区块和弹窗**

```html
<view class="account-row" v-if="user">
	<text v-if="user.username" class="account-bound">已绑定账号：{{ user.username }}</text>
	<template v-else>
		<text class="account-link" @click="openCredentialForm('set')">设置账号密码</text>
		<text class="account-link" @click="openCredentialForm('bind')">绑定已有桌面账号</text>
	</template>
</view>

<view class="modal-mask" v-if="credentialMode" @click="closeCredentialForm">
	<view class="modal-box" @click.stop>
		<text class="modal-title">{{ credentialMode === 'bind' ? '绑定已有桌面账号' : '设置账号密码' }}</text>
		<input class="modal-input" v-model="credentialUsername" placeholder="用户名" />
		<input class="modal-input" v-model="credentialPassword" placeholder="密码" password />
		<view class="modal-actions">
			<text class="modal-cancel" @click="closeCredentialForm">取消</text>
			<text class="modal-confirm" @click="submitCredentialForm">确定</text>
		</view>
	</view>
</view>
```

- [ ] **Step 5: `<style>` 里加**

```css
.account-row {
	margin: 10px 16px 0;
	padding: 0 2px;
	display: flex;
	gap: 16px;
}

.account-bound {
	font-size: 12px;
	color: var(--ink-soft);
}

.account-link {
	font-size: 12px;
	color: var(--margin);
}

.modal-mask {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: rgba(0, 0, 0, 0.5);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 999;
}

.modal-box {
	width: 260px;
	background-color: var(--paper);
	border: 1px solid rgba(232, 121, 249, 0.25);
	border-radius: 8px;
	padding: 20px;
}

.modal-title {
	display: block;
	font-family: Georgia, "Times New Roman", serif;
	font-size: 16px;
	font-weight: 700;
	color: var(--ink);
	margin-bottom: 14px;
}

.modal-input {
	display: block;
	border: 1px solid var(--rule);
	border-radius: 4px;
	padding: 8px 10px;
	margin-bottom: 12px;
	color: var(--ink);
	font-size: 14px;
}

.modal-actions {
	display: flex;
	justify-content: flex-end;
	gap: 20px;
}

.modal-cancel {
	color: var(--ink-soft);
	font-size: 14px;
}

.modal-confirm {
	color: var(--highlight-ink);
	font-size: 14px;
	font-weight: 700;
}
```

- [ ] **Step 6: 手动验证（微信开发者工具）**

1. 全新匿名账号（清缓存重进）：确认"我的"页头像卡片下方出现"设置账号密码"/"绑定已有桌面
   账号"两个入口，`user.username` 为空。
2. 点"设置账号密码"，输入一个新用户名密码，确认提交后弹窗关闭、账号区块变成"已绑定账号：
   xxx"，两个入口消失。
3. 清空模拟器缓存，重新进小程序，走一遍静默登录，确认"我的"页拿到的还是刚设置用户名密码
   的那个账号（`auth/me` 返回同一个 `id`/`username`）——这一步验证的是后端 `wx_mini` 没
   有变化，静默登录天然还是这条记录，不需要额外代码保证。
4. 准备另一个已经在桌面端（`en-elctron`，或直接用 `pytest` 里 `auth.register` 建的账号）
   注册过的用户名密码，在一个全新匿名小程序账号上点"绑定已有桌面账号"并提交，确认：
   - 弹窗关闭，账号区块显示绑定后的用户名；
   - 之前这个匿名账号名下如果有自建词库，去桌面端登录同一账号能看到（验证合并生效）；
   - 用错误密码提交，确认 toast 报错且不清空表单内容误导用户（`request()` 已有的失败
     toast 就够，不用额外处理）。

- [ ] **Step 7: Commit**

```bash
git add pages/my/my.vue
git commit -m "feat: 我的页新增账号密码设置/绑定已有桌面账号入口"
```

---

## Self-Review Notes

- **Spec coverage**：spec 里 4 个后端接口（profile/avatar/set-credentials/bind-account）
  对应 Task 2/3/4/6；`account_merge` 的三条合并规则（默认库合并去重、自建库改名过户、
  收藏去重）在 Task 5 逐条覆盖；前端资料卡片和账号入口分别是 Task 8/9；`requestDesktop.js`
  不用改静默登录逻辑，在 spec 里已说明原因，本计划没有对应任务是刻意的（不是遗漏）。
- **Type consistency**：`auth.update_profile`/`set_credentials`/`bind_account` 全部
  `(user_id: int, data: dict) -> dict` 签名一致；`account_merge.merge_libraries_and_
  favorites(source_user_id, target_user_id)` 的参数名在 Task 5/6 保持一致；前端
  `getToken`/`setToken` 在 Task 7 定义、Task 8/9 按同名使用。
- **已知不处理的边界（YAGNI，跟用户确认过不在本次范围内）**：`token` 单设备在线语义下，
  绑定后如果桌面端和小程序同时活跃会互相顶掉对方的 token——这是绑定前就存在的既有行为
  （`_issue_token` 一直是覆盖式签发），不是本次改动引入的问题，本计划不处理。

---

Plan complete and saved to `docs/superpowers/plans/2026-07-24-en-desktop-account-linking.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
