#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化 chess 数据库：若不存在则创建 chess 库，并建齐 5 张表。
本地/首次部署时手动运行一次：python3 scripts/init_chess_db.py
"""
import os
import sys

import pymysql

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.db import DB_CHESS_CONFIG  # noqa: E402


def create_database_if_missing() -> None:
    connection = pymysql.connect(
        host=DB_CHESS_CONFIG["host"],
        user=DB_CHESS_CONFIG["user"],
        password=DB_CHESS_CONFIG["password"],
        port=DB_CHESS_CONFIG["port"],
        charset=DB_CHESS_CONFIG.get("charset", "utf8mb4"),
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_CHESS_CONFIG['database']}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        connection.commit()
        print(f"数据库 `{DB_CHESS_CONFIG['database']}` 已就绪")
    finally:
        connection.close()


def create_tables() -> None:
    from app.database import Base, engine_chess
    from model.chess import ChessMove, ChessPlayer, ChessQueueEntry, ChessRoom, ChessSession

    tables = [
        ChessPlayer.__table__,
        ChessSession.__table__,
        ChessRoom.__table__,
        ChessMove.__table__,
        ChessQueueEntry.__table__,
    ]
    Base.metadata.create_all(bind=engine_chess, tables=tables)
    print(f"已创建/确认 {len(tables)} 张表：{', '.join(t.name for t in tables)}")


if __name__ == "__main__":
    create_database_if_missing()
    create_tables()
