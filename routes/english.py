# routes/english.py
"""
English 模块路由
"""
from fastapi import APIRouter, Request

from app.response import api_response
from service.english.words import (
    add as words_add,
    delete as words_delete,
    update as words_update,
    list_words,
)
from service.english.root import (
    add as root_add,
    delete as root_delete,
    update as root_update,
    list_roots,
)
from service.english.affix import (
    add as affix_add,
    delete as affix_delete,
    update as affix_update,
    list_affixes,
)
from service.english.dialogue import (
    add as dialogue_add,
    delete as dialogue_delete,
    update as dialogue_update,
    list_dialogues,
)
from service.english.living_speech import (
    add as living_speech_add,
    delete as living_speech_delete,
    update as living_speech_update,
    list_speeches,
)

router = APIRouter()


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


# ---------- 单词 ----------
@router.post("/words/add")
async def route_words_add(request: Request):
    return api_response(words_add(await _body(request)))


@router.post("/words/delete")
async def route_words_delete(request: Request):
    return api_response(words_delete(await _body(request)))


@router.post("/words/update")
async def route_words_update(request: Request):
    return api_response(words_update(await _body(request)))


@router.post("/words/list")
async def route_words_list(request: Request):
    return api_response(list_words(await _body(request)))


# ---------- 词根 ----------
@router.post("/root/add")
async def route_root_add(request: Request):
    return api_response(root_add(await _body(request)))


@router.post("/root/delete")
async def route_root_delete(request: Request):
    return api_response(root_delete(await _body(request)))


@router.post("/root/update")
async def route_root_update(request: Request):
    return api_response(root_update(await _body(request)))


@router.post("/root/list")
async def route_root_list(request: Request):
    return api_response(list_roots(await _body(request)))


# ---------- 词缀 ----------
@router.post("/affix/add")
async def route_affix_add(request: Request):
    return api_response(affix_add(await _body(request)))


@router.post("/affix/delete")
async def route_affix_delete(request: Request):
    return api_response(affix_delete(await _body(request)))


@router.post("/affix/update")
async def route_affix_update(request: Request):
    return api_response(affix_update(await _body(request)))


@router.get("/affix/list")
def route_affix_list():
    return api_response(list_affixes({}))


# ---------- 对话 ----------
@router.post("/dialogue/add")
async def route_dialogue_add(request: Request):
    return api_response(dialogue_add(await _body(request)))


@router.post("/dialogue/delete")
async def route_dialogue_delete(request: Request):
    return api_response(dialogue_delete(await _body(request)))


@router.post("/dialogue/update")
async def route_dialogue_update(request: Request):
    return api_response(dialogue_update(await _body(request)))


@router.get("/dialogue/list")
def route_dialogue_list():
    return api_response(list_dialogues({}))


# ---------- 生活用语 ----------
@router.post("/living-speech/add")
async def route_living_speech_add(request: Request):
    return api_response(living_speech_add(await _body(request)))


@router.post("/living-speech/delete")
async def route_living_speech_delete(request: Request):
    return api_response(living_speech_delete(await _body(request)))


@router.post("/living-speech/update")
async def route_living_speech_update(request: Request):
    return api_response(living_speech_update(await _body(request)))


@router.post("/living-speech/list")
async def route_living_speech_list(request: Request):
    return api_response(list_speeches(await _body(request)))
