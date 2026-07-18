# service/en_desktop/wechat_oauth.py
"""
微信开放平台"网站应用"扫码登录（OAuth2），与 chess 模块的小程序 code2session 是两套体系
"""
import requests

from config.wechat import (
    EN_DESKTOP_WECHAT_APP_ID,
    EN_DESKTOP_WECHAT_APP_SECRET,
    EN_MINI_WECHAT_APP_ID,
    EN_MINI_WECHAT_APP_SECRET,
)

ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"
MINI_SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


def exchange_code_for_openid(code: str) -> dict:
    """用授权 code 换取 access_token + openid"""
    resp = requests.get(
        ACCESS_TOKEN_URL,
        params={
            "appid": EN_DESKTOP_WECHAT_APP_ID,
            "secret": EN_DESKTOP_WECHAT_APP_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=5,
    )
    data = resp.json()
    if "errcode" in data:
        raise RuntimeError(data.get("errmsg", "微信登录失败"))
    return {"access_token": data["access_token"], "openid": data["openid"]}


def fetch_wechat_userinfo(access_token: str, openid: str) -> dict:
    """拉取微信昵称、头像"""
    resp = requests.get(
        USERINFO_URL,
        params={"access_token": access_token, "openid": openid, "lang": "zh_CN"},
        timeout=5,
    )
    data = resp.json()
    if "errcode" in data:
        raise RuntimeError(data.get("errmsg", "获取微信用户信息失败"))
    return {"nickname": data.get("nickname", ""), "headimgurl": data.get("headimgurl", "")}


def exchange_code_for_mini_openid(code: str) -> str:
    """en-mini 小程序 wx.login() 拿到的 code 换取 openid（code2session，与网页扫码登录是不同的 appid）"""
    if not EN_MINI_WECHAT_APP_ID or not EN_MINI_WECHAT_APP_SECRET:
        raise RuntimeError("小程序登录未配置：请设置 EN_MINI_WECHAT_APP_ID / EN_MINI_WECHAT_APP_SECRET")

    resp = requests.get(
        MINI_SESSION_URL,
        params={
            "appid": EN_MINI_WECHAT_APP_ID,
            "secret": EN_MINI_WECHAT_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        },
        timeout=5,
    )
    data = resp.json()
    if data.get("errcode"):
        raise RuntimeError(f"微信登录失败（{data['errcode']}）：{data.get('errmsg', '未知错误')}")
    return data["openid"]
