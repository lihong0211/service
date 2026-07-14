# config/db.py
"""
MySQL 连接配置：环境变量；若已安装 python-dotenv，自动加载项目根目录 .env。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
DB_BASE_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.environ.get("DB_PASSWORD"),
    "port": 3306,
    "charset": "utf8mb4",
    "autocommit": True,
}

DB_EN_CONFIG = DB_BASE_CONFIG | {
    "database": "english",
}
DB_PDD_CONFIG = DB_BASE_CONFIG | {
    "database": "pdd_report",
}

DB_CHESS_CONFIG = DB_BASE_CONFIG | {
    "host": os.environ.get("CHESS_DB_HOST", DB_BASE_CONFIG["host"]),
    "user": os.environ.get("CHESS_DB_USER", DB_BASE_CONFIG["user"]),
    "password": os.environ.get("CHESS_DB_PASSWORD", DB_BASE_CONFIG["password"]),
    "port": int(os.environ.get("CHESS_DB_PORT", DB_BASE_CONFIG["port"])),
    "database": os.environ.get("CHESS_DB_DATABASE", "chess"),
}
