# app/app.py
"""
应用包入口：导出 FastAPI `app` 与 `db`（与 service-home 分层一致）。
"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.database import (
    Base,
    SessionLocal,
    db,
    engine_en,
    engine_en_desktop,
    engine_pdd,
    engines,
    get_db,
)
from app.factory import create_app

app = create_app()

__all__ = [
    "app",
    "db",
    "get_db",
    "Base",
    "SessionLocal",
    "engine_en",
    "engine_en_desktop",
    "engine_pdd",
    "engines",
]
