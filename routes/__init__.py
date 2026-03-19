# routes/__init__.py
"""
路由模块 - 按业务拆分为 english / peach，统一挂载
"""
from fastapi import APIRouter

from routes.english import router as english_router
from routes.peach import router as peach_router

api_router = APIRouter()
api_router.include_router(english_router, prefix="/english", tags=["english"])
api_router.include_router(peach_router, prefix="/peach", tags=["peach"])
