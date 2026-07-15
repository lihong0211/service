# service/chess/auth.py
"""
Chess 登录服务：微信登录（code2session 换取 openid）+ 会话签发/校验
"""
import uuid
from datetime import datetime, timedelta

import requests

from app.database import db
from app.errors import unexpected_error_response
from config.wechat import WECHAT_APP_ID, WECHAT_APP_SECRET
from model.chess import ChessPlayer, ChessSession

SESSION_TTL = timedelta(days=7)
WECHAT_SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


class WechatLoginError(Exception):
    """微信 code2session 返回业务错误（如 code 无效/已使用）"""


def _fetch_wechat_openid(code: str) -> str:
    response = requests.get(
        WECHAT_SESSION_URL,
        params={
            "appid": WECHAT_APP_ID,
            "secret": WECHAT_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        },
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errcode"):
        raise WechatLoginError(f"微信登录失败（{data['errcode']}）：{data.get('errmsg', '未知错误')}")
    return data["openid"]


def _sanitize_avatar_url(avatar_url: str | None) -> str | None:
    """chooseAvatar 返回的可能是设备本地临时路径（wxfile://...），不是外网可访问的
    正式图片地址；只接受看起来像真实 URL 的值，避免把无法访问的本地路径存进数据库。"""
    if avatar_url and avatar_url.startswith(("http://", "https://")):
        return avatar_url
    return None


def login_with_wechat_code(code: str, nickname: str | None = None, avatar_url: str | None = None) -> dict:
    """微信登录：code 换取稳定 openid；nickname/avatar_url 由客户端 wx.getUserProfile() 提供"""
    trimmed_code = (code or "").strip()
    if not trimmed_code:
        return {"code": 400, "msg": "微信登录 code 不能为空"}

    if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
        return {"code": 500, "msg": "微信登录未配置：请设置 WECHAT_APP_ID / WECHAT_APP_SECRET"}

    avatar_url = _sanitize_avatar_url(avatar_url)

    try:
        open_id = _fetch_wechat_openid(trimmed_code)

        player = ChessPlayer.select_one_by({"open_id": open_id})
        if player is None:
            player_id = ChessPlayer.insert({
                "open_id": open_id,
                "nickname": nickname or "微信用户",
                "avatar_url": avatar_url,
            })
            player = ChessPlayer.get_by_id(player_id)
        elif nickname or avatar_url:
            update_data = {"id": player.id}
            if nickname:
                update_data["nickname"] = nickname
            if avatar_url:
                update_data["avatar_url"] = avatar_url
            ChessPlayer.update(update_data)
            player = ChessPlayer.get_by_id(player.id)

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
    except WechatLoginError as e:
        return {"code": 400, "msg": str(e)}
    except requests.RequestException:
        return {"code": 502, "msg": "微信服务暂不可用，请稍后重试"}
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
