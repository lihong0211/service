# routes/peach.py
"""
Peach 模块路由
"""
from fastapi import APIRouter, Request

from app.response import api_response
from service.peach.ali_report import (
    add as ali_report_add,
    get as ali_report_get,
    update as ali_report_update,
    list as ali_report_list,
)
from service.peach.check_result import (
    add as check_result_add,
    list as check_result_list,
)

router = APIRouter()


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


# ---------- 阿里报告 ----------
@router.post("/ali-report/add")
async def route_ali_report_add(request: Request):
    return api_response(ali_report_add(await _body(request)))


@router.post("/ali-report/get")
async def route_ali_report_get(request: Request):
    return api_response(ali_report_get(await _body(request)))


@router.post("/ali-report/update")
async def route_ali_report_update(request: Request):
    return api_response(ali_report_update(await _body(request)))


@router.post("/ali-report/list")
async def route_ali_report_list(request: Request):
    return api_response(ali_report_list(await _body(request)))


# ---------- 检查结果 ----------
@router.post("/check-result/add")
async def route_check_result_add(request: Request):
    return api_response(check_result_add(await _body(request)))


@router.post("/check-result/list")
async def route_check_result_list(request: Request):
    return api_response(check_result_list(await _body(request)))
