# routes/__init__.py
"""
路由模块 - 按业务拆分为 chess / english / peach / en-desktop，统一挂载
"""
from fastapi import APIRouter

from routes.chess import router as chess_router
from routes.en_desktop import router as en_desktop_router
from routes.english import router as english_router
from routes.peach import router as peach_router

api_router = APIRouter()
api_router.include_router(chess_router, prefix="/chess", tags=["chess"])
api_router.include_router(english_router, prefix="/english", tags=["english"])
api_router.include_router(peach_router, prefix="/peach", tags=["peach"])
api_router.include_router(en_desktop_router, prefix="/en-desktop", tags=["en-desktop"])
