from config.db import DB_BASE_CONFIG, DB_CHESS_CONFIG


def test_chess_db_config_has_dedicated_database_name():
    assert DB_CHESS_CONFIG["database"] == "chess"


def test_chess_db_config_falls_back_to_base_host_and_user():
    assert DB_CHESS_CONFIG["host"] == DB_BASE_CONFIG["host"]
    assert DB_CHESS_CONFIG["user"] == DB_BASE_CONFIG["user"]


def test_chess_engine_is_registered():
    from sqlalchemy.engine import Engine

    from app.database import engines

    assert "chess" in engines
    assert isinstance(engines["chess"], Engine)
