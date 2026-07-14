from service.chess import auth


def test_login_creates_player_and_session(chess_db):
    result = auth.login_with_wechat_code("wx-login-42")

    assert result["code"] == 200
    assert result["data"]["player"]["nickname"] == "棋友 42"
    assert result["data"]["session"]["token"]


def test_login_is_idempotent_for_same_code(chess_db):
    first = auth.login_with_wechat_code("wx-login-42")
    second = auth.login_with_wechat_code("wx-login-42")

    assert first["data"]["player"]["id"] == second["data"]["player"]["id"]
    assert first["data"]["session"]["token"] != second["data"]["session"]["token"]


def test_login_rejects_empty_code(chess_db):
    result = auth.login_with_wechat_code("   ")

    assert result["code"] == 400


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
