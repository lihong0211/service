"""
en-desktop 认证服务测试
"""
from datetime import datetime, timedelta

from model.en_desktop import EnDesktopUser, EnDesktopWordLibrary
from service.en_desktop import auth


def test_register_login_me_roundtrip(en_desktop_db):
    result = auth.register({"username": "alice", "password": "secret"})
    assert result["code"] == 200
    token = result["data"]["token"]
    assert token
    assert result["data"]["user"]["username"] == "alice"
    # 公开输出绝不包含敏感字段
    assert "password" not in result["data"]["user"]
    assert "token" not in result["data"]["user"]

    login = auth.login({"username": "alice", "password": "secret"})
    assert login["code"] == 200
    new_token = login["data"]["token"]
    # 重新登录签发新 token（单设备在线），旧 token 失效
    assert new_token != token
    assert auth.me(token)["code"] == 401
    me = auth.me(new_token)
    assert me["code"] == 200
    assert me["data"]["username"] == "alice"


def test_register_duplicate_username(en_desktop_db):
    auth.register({"username": "alice", "password": "secret"})
    result = auth.register({"username": "alice", "password": "other"})
    assert result["code"] == 400
    assert "已存在" in result["msg"]


def test_register_validates_length(en_desktop_db):
    assert auth.register({"username": "", "password": "secret"})["code"] == 400
    assert auth.register({"username": "a" * 21, "password": "secret"})["code"] == 400
    assert auth.register({"username": "bob", "password": "ab"})["code"] == 400


def test_login_wrong_password(en_desktop_db):
    auth.register({"username": "alice", "password": "secret"})
    result = auth.login({"username": "alice", "password": "wrong"})
    assert result["code"] == 400
    result = auth.login({"username": "nobody", "password": "secret"})
    assert result["code"] == 400


def test_me_expired_token(en_desktop_db):
    result = auth.register({"username": "alice", "password": "secret"})
    token = result["data"]["token"]
    user = EnDesktopUser.select_one_by({"username": "alice"})
    EnDesktopUser.update(
        {"id": user.id, "token_expires_at": datetime.now() - timedelta(days=1)}
    )
    assert auth.me(token)["code"] == 401


def test_me_without_token(en_desktop_db):
    assert auth.me(None)["code"] == 401
    assert auth.me("nonexistent")["code"] == 401


def test_wechat_login_creates_and_updates_user(en_desktop_db, monkeypatch):
    monkeypatch.setattr(
        auth.wechat_oauth,
        "exchange_code_for_openid",
        lambda code: {"access_token": "at", "openid": "openid-1"},
    )
    monkeypatch.setattr(
        auth.wechat_oauth,
        "fetch_wechat_userinfo",
        lambda at, openid: {"nickname": "微信用户", "headimgurl": "https://x/a.png"},
    )

    result = auth.wechat_login({"code": "any-code"})
    assert result["code"] == 200
    assert result["data"]["user"]["wx"] == "openid-1"
    assert result["data"]["user"]["nickname"] == "微信用户"

    # 二次登录复用同一用户并同步资料
    monkeypatch.setattr(
        auth.wechat_oauth,
        "fetch_wechat_userinfo",
        lambda at, openid: {"nickname": "新昵称", "headimgurl": "https://x/b.png"},
    )
    again = auth.wechat_login({"code": "another-code"})
    assert again["code"] == 200
    assert again["data"]["user"]["nickname"] == "新昵称"
    assert len(EnDesktopUser.select_by({"wx": "openid-1"})) == 1


def test_wechat_login_error(en_desktop_db, monkeypatch):
    def boom(code):
        raise RuntimeError("invalid code")

    monkeypatch.setattr(auth.wechat_oauth, "exchange_code_for_openid", boom)
    result = auth.wechat_login({"code": "bad"})
    assert result["code"] == 500
    assert result["msg"] == "invalid code"

    assert auth.wechat_login({})["code"] == 400


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


def test_bind_account_fills_in_missing_nickname_and_avatar(en_desktop_db, monkeypatch):
    """target（桌面账号密码注册）从没设置过昵称头像；source（小程序）已经设置过——
    合并后 target 应该拿到 source 的昵称头像，而不是保持空。"""
    target = auth.register({"username": "alice", "password": "secret"})
    target_id = target["data"]["user"]["id"]

    monkeypatch.setattr(auth.wechat_oauth, "exchange_code_for_mini_openid", lambda code: "mini-openid-1")
    mini = auth.mini_login({"code": "any"})
    source_id = mini["data"]["user"]["id"]
    auth.update_profile(source_id, {"nickname": "cdut007"})
    EnDesktopUser.update({"id": source_id, "avatar": "https://x.test/avatar.jpg"})

    result = auth.bind_account(source_id, {"username": "alice", "password": "secret"})
    assert result["code"] == 200
    assert result["data"]["user"]["nickname"] == "cdut007"
    assert result["data"]["user"]["avatar"] == "https://x.test/avatar.jpg"


def test_bind_account_keeps_targets_own_nickname_and_avatar(en_desktop_db, monkeypatch):
    """target 已经有自己的昵称头像时，不能被 source 的覆盖掉。"""
    target = auth.register({"username": "alice", "password": "secret"})
    target_id = target["data"]["user"]["id"]
    auth.update_profile(target_id, {"nickname": "桌面昵称"})
    EnDesktopUser.update({"id": target_id, "avatar": "https://x.test/desktop-avatar.jpg"})

    monkeypatch.setattr(auth.wechat_oauth, "exchange_code_for_mini_openid", lambda code: "mini-openid-1")
    mini = auth.mini_login({"code": "any"})
    source_id = mini["data"]["user"]["id"]
    auth.update_profile(source_id, {"nickname": "cdut007"})

    result = auth.bind_account(source_id, {"username": "alice", "password": "secret"})
    assert result["code"] == 200
    assert result["data"]["user"]["nickname"] == "桌面昵称"
    assert result["data"]["user"]["avatar"] == "https://x.test/desktop-avatar.jpg"


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
