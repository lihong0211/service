# service/chess/auth.py
"""
Chess 登录服务：mock 微信登录 + 会话签发/校验
"""
import hashlib
import re
import uuid
from datetime import datetime, timedelta

from app.database import db
from app.errors import unexpected_error_response
from model.chess import ChessPlayer, ChessSession

SESSION_TTL = timedelta(days=7)


def _mock_open_id(code: str) -> str:
    return f"mock_{code}"


def _mock_nickname(code: str) -> str:
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    match = re.search(r"(\d+)$", code)
    suffix = match.group(1) if match else str(int(digest[:4], 16) % 10000 or 1)
    return f"棋友 {suffix}"


def login_with_wechat_code(code: str) -> dict:
    """mock 微信登录：同一 code 始终对应同一棋手，每次登录签发新会话"""
    trimmed_code = (code or "").strip()
    if not trimmed_code:
        return {"code": 400, "msg": "微信登录 code 不能为空"}

    try:
        open_id = _mock_open_id(trimmed_code)
        player = ChessPlayer.select_one_by({"open_id": open_id})
        if player is None:
            player_id = ChessPlayer.insert({
                "open_id": open_id,
                "nickname": _mock_nickname(trimmed_code),
            })
            player = ChessPlayer.get_by_id(player_id)

        expires_at = datetime.now() + SESSION_TTL
        token = str(uuid.uuid4())
        ChessSession.insert({
            "token": token,
            "player_id": player.id,
            "expires_at": expires_at,
        })

        return {
            "code": 200,
            "data": {
                "player": {
                    "id": player.id,
                    "nickname": player.nickname,
                    "avatar_url": player.avatar_url,
                },
                "session": {
                    "token": token,
                    "player_id": player.id,
                    "expires_at": expires_at.isoformat(),
                },
            },
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def require_session(token: str):
    """校验会话令牌，过期则软删除并返回 None"""
    session = ChessSession.select_one_by({"token": token})
    if session is None:
        return None
    if session.expires_at <= datetime.now():
        ChessSession.delete(session.id)
        return None
    return session


def get_player(player_id: int):
    return ChessPlayer.get_by_id(player_id)
