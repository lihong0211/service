"""
en-desktop 认证服务测试
"""
from datetime import datetime, timedelta

from model.en_desktop import EnDesktopUser
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
