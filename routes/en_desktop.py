# routes/en_desktop.py
"""
en-desktop 模块路由（记单词桌面客户端后端）

不用 app.response.api_response：桌面客户端的 axios 拦截器只在 HTTP 200 的
成功回调里检查 body.code（401 触发重新登录），业务错误映射成 4xx/5xx
会直接走进 axios 的 reject 分支，破坏客户端既有契约。
"""
from fastapi import APIRouter, BackgroundTasks, File, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from service.en_desktop import affixes as affixes_service
from service.en_desktop import auth as auth_service
from service.en_desktop import avatar as avatar_service
from service.en_desktop import daily_expressions as daily_expressions_service
from service.en_desktop import libraries as libraries_service
from service.en_desktop import roots as roots_service
from service.en_desktop import sentences as sentences_service
from service.en_desktop import users as users_service
from service.en_desktop import words as words_service

router = APIRouter()

UNAUTHORIZED = {"code": 401, "msg": "未登录或登录已过期"}


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[len("Bearer "):]


def _current_user_id(authorization: str | None) -> int | None:
    user = auth_service.resolve_user_by_token(_bearer_token(authorization))
    return user.id if user else None


def _json_200(body: dict) -> JSONResponse:
    return JSONResponse(content=body, status_code=200, media_type="application/json; charset=utf-8")


# ---------- 认证 ----------
@router.post("/auth/register")
async def route_auth_register(request: Request):
    return _json_200(auth_service.register(await _body(request)))


@router.post("/auth/login")
async def route_auth_login(request: Request):
    return _json_200(auth_service.login(await _body(request)))


@router.post("/auth/wechat/login")
async def route_auth_wechat_login(request: Request):
    return _json_200(auth_service.wechat_login(await _body(request)))


@router.post("/auth/wechat/mini-login")
async def route_auth_wechat_mini_login(request: Request):
    return _json_200(auth_service.mini_login(await _body(request)))


@router.get("/auth/me")
async def route_auth_me(authorization: str | None = Header(None)):
    return _json_200(auth_service.me(_bearer_token(authorization)))


@router.post("/auth/profile")
async def route_auth_profile(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(auth_service.update_profile(user_id, await _body(request)))


@router.post("/auth/avatar")
async def route_auth_avatar(
    file: UploadFile = File(...), authorization: str | None = Header(None)
):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    content = await file.read()
    return _json_200(avatar_service.save_avatar(user_id, content))


@router.post("/auth/set-credentials")
async def route_auth_set_credentials(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(auth_service.set_credentials(user_id, await _body(request)))


@router.post("/auth/bind-account")
async def route_auth_bind_account(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(auth_service.bind_account(user_id, await _body(request)))


# ---------- 用户 ----------
@router.get("/users/list")
async def route_users_list(
    page: int = Query(1, description="页码，从1开始"),
    page_size: int = Query(10, description="每页记录数", le=10000),
    active: bool | None = Query(None, description="是否激活"),
):
    return _json_200(users_service.list_users(page, page_size, active))


@router.get("/users/{user_id}")
async def route_users_get(user_id: int):
    return _json_200(users_service.get_user(user_id))


@router.post("/users/add")
async def route_users_add(request: Request):
    return _json_200(users_service.add_user(await _body(request)))


@router.post("/users/update")
async def route_users_update(request: Request, user_id: int = Query(..., description="用户ID")):
    return _json_200(users_service.update_user(user_id, await _body(request)))


@router.post("/users/delete")
async def route_users_delete(user_id: int = Query(..., description="用户ID")):
    return _json_200(users_service.delete_user(user_id))


@router.post("/users/activate")
async def route_users_activate(
    user_id: int = Query(..., description="用户ID"),
    active: bool = Query(..., description="激活状态"),
):
    return _json_200(users_service.activate_user(user_id, active))


# ---------- 单词 ----------
@router.get("/words/list")
async def route_words_list(
    page: int = Query(1, description="页码，从1开始"),
    page_size: int = Query(10, description="每页记录数", le=10000),
    search: str | None = Query(None, description="按单词模糊搜索"),
    authorization: str | None = Header(None),
):
    user_id = _current_user_id(authorization)
    return _json_200(words_service.list_words(page, page_size, search, user_id))


@router.get("/words/{word_id}")
async def route_words_get(word_id: int):
    return _json_200(words_service.get_word(word_id))


@router.post("/words/add")
async def route_words_add(
    request: Request, background_tasks: BackgroundTasks, authorization: str | None = Header(None)
):
    # user_id 可选：body 带 library_id（收藏进词库）时才要求登录
    new_meaning_ids: list[int] = []
    result = words_service.add_word(
        await _body(request),
        user_id=_current_user_id(authorization),
        on_new_meanings=new_meaning_ids.extend,
    )
    # 新词落库成功后才补例句：响应先返回，例句+音频生成放到后台跑，不拖慢"新增单词"这个操作
    for meaning_id in new_meaning_ids:
        background_tasks.add_task(sentences_service.generate_and_attach_sentence, meaning_id)
    return _json_200(result)


@router.post("/words/lookup")
async def route_words_lookup(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    return _json_200(words_service.lookup(await _body(request), user_id))


@router.post("/words/remove-from-library")
async def route_words_remove_from_library(
    request: Request, authorization: str | None = Header(None)
):
    user_id = _current_user_id(authorization)
    return _json_200(words_service.remove_from_library(await _body(request), user_id))


@router.post("/words/update")
async def route_words_update(request: Request, word_id: int = Query(..., description="wordID")):
    return _json_200(words_service.update_word(word_id, await _body(request)))


@router.post("/words/delete")
async def route_words_delete(word_id: int = Query(..., description="wordID")):
    return _json_200(words_service.delete_word(word_id))


# ---------- 日常用语 ----------
@router.get("/daily-expressions/list")
async def route_daily_expressions_list(
    page: int = Query(1, description="页码，从1开始"),
    page_size: int = Query(10, description="每页记录数", le=10000),
    search: str | None = Query(None, description="按短语模糊搜索"),
):
    return _json_200(daily_expressions_service.list_expressions(page, page_size, search))


@router.get("/daily-expressions/{expression_id}")
async def route_daily_expressions_get(expression_id: int):
    return _json_200(daily_expressions_service.get_expression(expression_id))


@router.post("/daily-expressions/add")
async def route_daily_expressions_add(request: Request):
    return _json_200(daily_expressions_service.add_expression(await _body(request)))


@router.post("/daily-expressions/update")
async def route_daily_expressions_update(
    request: Request, expression_id: int = Query(..., description="记录ID")
):
    return _json_200(
        daily_expressions_service.update_expression(expression_id, await _body(request))
    )


@router.post("/daily-expressions/delete")
async def route_daily_expressions_delete(expression_id: int = Query(..., description="记录ID")):
    return _json_200(daily_expressions_service.delete_expression(expression_id))


# ---------- 词根 ----------
@router.get("/roots/list")
async def route_roots_list():
    return _json_200(roots_service.list_roots())


@router.post("/roots/add")
async def route_roots_add(request: Request):
    return _json_200(roots_service.add_root(await _body(request)))


@router.post("/roots/update")
async def route_roots_update(request: Request, root_id: int = Query(..., description="记录ID")):
    return _json_200(roots_service.update_root(root_id, await _body(request)))


@router.post("/roots/delete")
async def route_roots_delete(root_id: int = Query(..., description="记录ID")):
    return _json_200(roots_service.delete_root(root_id))


@router.post("/roots/add-word")
async def route_roots_add_word(request: Request):
    body = await _body(request)
    return _json_200(roots_service.add_word(body.get("root_id"), body.get("word_id")))


@router.post("/roots/remove-word")
async def route_roots_remove_word(request: Request):
    body = await _body(request)
    return _json_200(roots_service.remove_word(body.get("root_id"), body.get("word_id")))


# ---------- 词缀 ----------
@router.get("/affixes/list")
async def route_affixes_list():
    return _json_200(affixes_service.list_affixes())


@router.post("/affixes/add")
async def route_affixes_add(request: Request):
    return _json_200(affixes_service.add_affix(await _body(request)))


@router.post("/affixes/update")
async def route_affixes_update(request: Request, affix_id: int = Query(..., description="记录ID")):
    return _json_200(affixes_service.update_affix(affix_id, await _body(request)))


@router.post("/affixes/delete")
async def route_affixes_delete(affix_id: int = Query(..., description="记录ID")):
    return _json_200(affixes_service.delete_affix(affix_id))


@router.post("/affixes/add-word")
async def route_affixes_add_word(request: Request):
    body = await _body(request)
    return _json_200(affixes_service.add_word(body.get("affix_id"), body.get("word_id")))


@router.post("/affixes/remove-word")
async def route_affixes_remove_word(request: Request):
    body = await _body(request)
    return _json_200(affixes_service.remove_word(body.get("affix_id"), body.get("word_id")))


# ---------- 词库（歌单式，公共词库浏览不需要登录，个人词库需要登录） ----------
@router.get("/libraries/public")
async def route_libraries_public(authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    return _json_200(libraries_service.list_public_libraries(user_id))


@router.get("/libraries/favorites")
async def route_libraries_favorites(authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(libraries_service.list_favorites(user_id))


@router.post("/libraries/favorite")
async def route_libraries_favorite(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    body = await _body(request)
    return _json_200(libraries_service.favorite_library(user_id, body.get("library_id")))


@router.post("/libraries/unfavorite")
async def route_libraries_unfavorite(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    body = await _body(request)
    return _json_200(libraries_service.unfavorite_library(user_id, body.get("library_id")))


@router.get("/libraries/list")
async def route_libraries_list(authorization: str | None = Header(None)):
    # 未登录没有"自建词库"，返回空列表；登录后看自己的全部词库
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200({"code": 200, "msg": "success", "data": []})
    return _json_200(libraries_service.list_libraries(user_id))


@router.post("/libraries/add")
async def route_libraries_add(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(libraries_service.add_library(user_id, await _body(request)))


@router.post("/libraries/update")
async def route_libraries_update(
    request: Request,
    library_id: int = Query(..., description="词库ID"),
    authorization: str | None = Header(None),
):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(libraries_service.update_library(user_id, library_id, await _body(request)))


@router.post("/libraries/delete")
async def route_libraries_delete(
    library_id: int = Query(..., description="词库ID"),
    authorization: str | None = Header(None),
):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(libraries_service.delete_library(user_id, library_id))


@router.get("/libraries/{library_id}/words")
async def route_libraries_words(
    library_id: int,
    page: int = Query(1, description="页码，从1开始"),
    page_size: int = Query(10, description="每页记录数", le=10000),
    search: str | None = Query(None, description="按单词模糊搜索"),
    authorization: str | None = Header(None),
):
    # 不登录也能看公共词库里的单词，私有词库仍然会被 service 层挡掉
    user_id = _current_user_id(authorization)
    return _json_200(
        libraries_service.library_words(user_id, library_id, page, page_size, search)
    )


@router.post("/libraries/add-word")
async def route_libraries_add_word(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(libraries_service.add_word_to_library(user_id, await _body(request)))


@router.post("/libraries/remove-word")
async def route_libraries_remove_word(request: Request, authorization: str | None = Header(None)):
    user_id = _current_user_id(authorization)
    if user_id is None:
        return _json_200(UNAUTHORIZED)
    return _json_200(libraries_service.remove_word_from_library(user_id, await _body(request)))
