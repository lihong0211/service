# routes/chess.py
"""
Chess 模块路由
"""
from fastapi import APIRouter, Header, Request

from app.response import api_response
from service.chess.auth import login_with_wechat_code, require_session
from service.chess.matchmaking import (
    get_room,
    get_status,
    join_queue,
    leave_queue,
    submit_move,
)

router = APIRouter()


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[len("Bearer "):]


def _authenticated_player_id(authorization: str | None):
    token = _bearer_token(authorization)
    session = require_session(token) if token else None
    return session.player_id if session else None


# ---------- 登录 ----------
@router.post("/auth/wechat-login")
async def route_wechat_login(request: Request):
    body = await _body(request)
    return api_response(login_with_wechat_code(
        body.get("code", ""),
        nickname=body.get("nickname"),
        avatar_url=body.get("avatar_url"),
    ))


# ---------- 匹配 ----------
@router.post("/matchmaking/join")
async def route_matchmaking_join(authorization: str | None = Header(None)):
    player_id = _authenticated_player_id(authorization)
    if player_id is None:
        return api_response({"code": 401, "msg": "登录已失效"})
    return api_response(join_queue(player_id))


@router.post("/matchmaking/leave")
async def route_matchmaking_leave(authorization: str | None = Header(None)):
    player_id = _authenticated_player_id(authorization)
    if player_id is None:
        return api_response({"code": 401, "msg": "登录已失效"})
    return api_response(leave_queue(player_id))


@router.get("/matchmaking/status")
async def route_matchmaking_status(authorization: str | None = Header(None)):
    player_id = _authenticated_player_id(authorization)
    if player_id is None:
        return api_response({"code": 401, "msg": "登录已失效"})
    return api_response(get_status(player_id))


# ---------- 房间 ----------
@router.get("/rooms/{room_id}")
async def route_room_get(room_id: int):
    return api_response(get_room(room_id))


@router.post("/rooms/{room_id}/move")
async def route_room_move(room_id: int, request: Request, authorization: str | None = Header(None)):
    player_id = _authenticated_player_id(authorization)
    if player_id is None:
        return api_response({"code": 401, "msg": "登录已失效"})

    body = await _body(request)
    return api_response(
        submit_move(room_id, player_id, body.get("from", {}), body.get("to", {}))
    )
