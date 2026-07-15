import pytest
import requests

from service.chess import auth


@pytest.fixture(autouse=True)
def _mock_wechat_credentials(monkeypatch):
    monkeypatch.setattr(auth, "WECHAT_APP_ID", "test-app-id")
    monkeypatch.setattr(auth, "WECHAT_APP_SECRET", "test-app-secret")


@pytest.fixture(autouse=True)
def _mock_wechat_openid(monkeypatch):
    monkeypatch.setattr(auth, "_fetch_wechat_openid", lambda code: f"openid_{code}")


def test_login_creates_player_with_client_provided_nickname(chess_db):
    result = auth.login_with_wechat_code("wx-login-42", nickname="棋类爱好者")

    assert result["code"] == 200
    assert result["data"]["player"]["nickname"] == "棋类爱好者"
    assert result["data"]["session"]["token"]


def test_login_defaults_nickname_when_not_provided(chess_db):
    result = auth.login_with_wechat_code("wx-login-1")

    assert result["data"]["player"]["nickname"] == "微信用户"


def test_login_is_idempotent_for_same_openid(chess_db):
    first = auth.login_with_wechat_code("wx-login-42")
    second = auth.login_with_wechat_code("wx-login-42")

    assert first["data"]["player"]["id"] == second["data"]["player"]["id"]
    assert first["data"]["session"]["token"] != second["data"]["session"]["token"]


def test_login_updates_nickname_on_repeat_login(chess_db):
    first = auth.login_with_wechat_code("wx-login-42", nickname="旧昵称")
    second = auth.login_with_wechat_code("wx-login-42", nickname="新昵称")

    assert first["data"]["player"]["id"] == second["data"]["player"]["id"]
    assert second["data"]["player"]["nickname"] == "新昵称"


def test_login_keeps_existing_nickname_when_not_resent(chess_db):
    first = auth.login_with_wechat_code("wx-login-42", nickname="旧昵称")
    second = auth.login_with_wechat_code("wx-login-42")

    assert first["data"]["player"]["id"] == second["data"]["player"]["id"]
    assert second["data"]["player"]["nickname"] == "旧昵称"


def test_login_stores_real_http_avatar_url(chess_db):
    result = auth.login_with_wechat_code(
        "wx-login-42", avatar_url="https://example.com/avatar.jpg"
    )

    assert result["data"]["player"]["avatar_url"] == "https://example.com/avatar.jpg"


def test_login_ignores_local_device_avatar_path(chess_db):
    result = auth.login_with_wechat_code(
        "wx-login-1", avatar_url="wxfile://tmp_avatar123.jpg"
    )

    assert result["data"]["player"]["avatar_url"] is None


def test_login_rejects_empty_code(chess_db):
    result = auth.login_with_wechat_code("   ")

    assert result["code"] == 400


def test_login_returns_500_when_credentials_missing(chess_db, monkeypatch):
    monkeypatch.setattr(auth, "WECHAT_APP_ID", "")

    result = auth.login_with_wechat_code("wx-login-1")

    assert result["code"] == 500


def test_login_returns_400_when_wechat_reports_business_error(chess_db, monkeypatch):
    def _raise(code):
        raise auth.WechatLoginError("微信登录失败（40163）：code been used")

    monkeypatch.setattr(auth, "_fetch_wechat_openid", _raise)

    result = auth.login_with_wechat_code("wx-login-1")

    assert result["code"] == 400


def test_login_returns_502_when_wechat_unreachable(chess_db, monkeypatch):
    def _raise(code):
        raise requests.ConnectionError("network unreachable")

    monkeypatch.setattr(auth, "_fetch_wechat_openid", _raise)

    result = auth.login_with_wechat_code("wx-login-1")

    assert result["code"] == 502


def test_require_session_returns_none_for_unknown_token(chess_db):
    assert auth.require_session("does-not-exist") is None


def test_require_session_returns_session_for_valid_token(chess_db):
    login_result = auth.login_with_wechat_code("wx-login-7")
    token = login_result["data"]["session"]["token"]

    session = auth.require_session(token)

    assert session is not None
    assert session.token == token


def test_require_session_rejects_expired_token(chess_db, monkeypatch):
    import datetime as dt

    from service.chess import auth as auth_module

    login_result = auth.login_with_wechat_code("wx-login-99")
    token = login_result["data"]["session"]["token"]

    future = dt.datetime.now() + dt.timedelta(days=8)

    class _FrozenDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return future

    monkeypatch.setattr(auth_module, "datetime", _FrozenDateTime)

    assert auth.require_session(token) is None
