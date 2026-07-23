# service/en_desktop/auth.py
"""
en-desktop 认证服务：账号密码注册/登录 + 微信扫码登录 + token 签发校验。
token 存 users 表（单设备在线），30 天有效，与桌面客户端既有契约一致。
"""
from datetime import datetime, timedelta

from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import EnDesktopUser
from service.en_desktop import account_merge, wechat_oauth
from service.en_desktop.security import generate_token, hash_password, verify_password

TOKEN_VALID_DAYS = 30


def _issue_token(user: EnDesktopUser) -> str:
    token = generate_token()
    EnDesktopUser.update(
        {
            "id": user.id,
            "token": token,
            "token_expires_at": datetime.now() + timedelta(days=TOKEN_VALID_DAYS),
        }
    )
    return token


def _auth_success(user_id: int) -> dict:
    user = EnDesktopUser.get_by_id(user_id)
    token = _issue_token(user)
    return {
        "code": 200,
        "msg": "success",
        "data": {"token": token, "user": EnDesktopUser.get_by_id(user_id).public_dict()},
    }


def register(data: dict) -> dict:
    """账号密码注册，成功即登录"""
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not 1 <= len(username) <= 20:
        return {"code": 400, "msg": "用户名长度需在1-20个字符"}
    if not 3 <= len(password) <= 100:
        return {"code": 400, "msg": "密码长度需在3-100个字符"}

    try:
        if EnDesktopUser.select_one_by({"username": username}):
            return {"code": 400, "msg": "用户名已存在"}

        user_id = EnDesktopUser.insert(
            {"username": username, "password": hash_password(password)}
        )
        return _auth_success(user_id)
    except Exception as e:
        return unexpected_error_response(e, db.session)


def login(data: dict) -> dict:
    """账号密码登录"""
    username = data.get("username") or ""
    password = data.get("password") or ""

    try:
        user = EnDesktopUser.select_one_by({"username": username})
        if not user or not user.password or not verify_password(password, user.password):
            return {"code": 400, "msg": "用户名或密码错误"}
        return _auth_success(user.id)
    except Exception as e:
        return unexpected_error_response(e, db.session)


def wechat_login(data: dict) -> dict:
    """微信扫码登录：code 换 openid，按 openid 建/更新用户"""
    code = data.get("code") or ""
    if not code:
        return {"code": 400, "msg": "缺少微信授权 code"}

    try:
        token_data = wechat_oauth.exchange_code_for_openid(code)
        userinfo = wechat_oauth.fetch_wechat_userinfo(
            token_data["access_token"], token_data["openid"]
        )
    except RuntimeError as e:
        return {"code": 500, "msg": str(e)}
    except Exception as e:
        return unexpected_error_response(e)

    try:
        openid = token_data["openid"]
        user = EnDesktopUser.select_one_by({"wx": openid})
        profile = {"nickname": userinfo["nickname"], "avatar": userinfo["headimgurl"]}
        if not user:
            user_id = EnDesktopUser.insert({"wx": openid, **profile})
        else:
            user_id = EnDesktopUser.update({"id": user.id, **profile})
        return _auth_success(user_id)
    except Exception as e:
        return unexpected_error_response(e, db.session)


def mini_login(data: dict) -> dict:
    """en-mini 小程序登录：code2session 换 openid，按 wx_mini 建/更新用户"""
    code = data.get("code") or ""
    if not code:
        return {"code": 400, "msg": "缺少微信登录 code"}

    try:
        openid = wechat_oauth.exchange_code_for_mini_openid(code)
    except RuntimeError as e:
        return {"code": 500, "msg": str(e)}
    except Exception as e:
        return unexpected_error_response(e)

    try:
        user = EnDesktopUser.select_one_by({"wx_mini": openid})
        if not user:
            user_id = EnDesktopUser.insert({"wx_mini": openid, "nickname": "微信用户"})
        else:
            user_id = user.id
        return _auth_success(user_id)
    except Exception as e:
        return unexpected_error_response(e, db.session)


def resolve_user_by_token(token: str | None) -> EnDesktopUser | None:
    """按 token 查用户并校验有效期，无效返回 None"""
    if not token:
        return None
    user = EnDesktopUser.select_one_by({"token": token})
    if not user:
        return None
    if user.token_expires_at and user.token_expires_at < datetime.now():
        return None
    return user


def me(token: str | None) -> dict:
    """获取当前登录用户；客户端依赖 code=401 触发重新登录"""
    try:
        user = resolve_user_by_token(token)
        if not user:
            return {"code": 401, "msg": "未登录或登录已过期"}
        return {"code": 200, "msg": "success", "data": user.public_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)


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

        # target 没设置过昵称/头像时，用 source 的补上（比如小程序端已经填过资料，
        # 桌面账号只是纯用户名密码注册，昵称头像全是空的）；target 已有的不覆盖
        if not target.nickname and source.nickname:
            target.nickname = source.nickname
        if not target.avatar and source.avatar:
            target.avatar = source.avatar

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
