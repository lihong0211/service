# Chess Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port chess-server's Xiangqi (Chinese chess) rules/auth/matchmaking into a new Python `chess` module inside this FastAPI app, following the existing `routes -> service -> model` layering, backed by a dedicated MySQL database.

**Architecture:** `service/chess/rules.py` is a pure-Python, dependency-free Xiangqi rules engine (board, legal moves, check/checkmate/stalemate detection, FEN serialization). `service/chess/auth.py` and `service/chess/matchmaking.py` are DB-backed services following the project's `BaseModel` conventions, storing sessions/rooms/moves/queue in a new `chess` MySQL database (via a new `__bind_key__ = "chess"`). `routes/chess.py` exposes everything as REST endpoints mounted at `/chess`, polled by clients instead of pushed over WebSocket (no WebSocket layer is ported, since production runs multiple uvicorn workers and in-memory/socket state can't be shared across them).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (existing versions in `requirements.txt`), pytest (new), SQLite in-memory (test-only, for service-layer tests).

## Global Constraints

- Follow the existing `routes/ -> service/ -> model/` layering, mirroring `english`/`peach` (see `routes/english.py`, `service/english/words.py`, `model/english/words.py`).
- All new tables extend the project's `BaseModel` (`model/common/base_model.py`) — soft delete via `deleted_at`, `insert`/`update`/`builder_query`/`select_one_by`/`force_delete` conventions — with `__bind_key__ = "chess"`.
- Chess data lives in a dedicated `chess` MySQL database with its own `DB_CHESS_CONFIG` and `CHESS_DB_*` env vars — never reuse `engine_en`.
- `service/chess/rules.py` has zero database or FastAPI imports — pure Python, unit-testable in isolation.
- No WebSocket layer. All state changes are exposed via polling REST endpoints only; chess-server's `ws`-based push is not ported.
- Service functions return `{code, msg}` / `{code, msg, data}` dicts wrapped by `app/response.py`'s `api_response`; unexpected exceptions go through `app/errors.py`'s `unexpected_error_response`.
- Service-layer tests (`auth`, `matchmaking`, models) run against an in-memory SQLite engine via a pytest fixture that overrides the request-scoped DB session — no real MySQL is required to run the test suite.
- `chess-server/` itself is not modified.
- Run every test with `python3 -m pytest ...` (not bare `pytest`) so the repo root is on `sys.path` and `import service.chess...` / `import model.chess...` resolve correctly.
- Importing anything under `model.chess` or `service.chess` transitively imports `app.app`, which calls `create_app()` at module load time (same as `model.english.words` already does) — this requires a working `.env` with `DB_USER`/`DB_PASSWORD` set, which this project already requires to run at all.

---

### Task 1: Chess database config and engine wiring

**Files:**
- Modify: `config/db.py`
- Modify: `app/database.py`
- Modify: `.env.example`
- Test: `tests/chess/test_db_config.py`

**Interfaces:**
- Consumes: nothing (foundational task)
- Produces: `config.db.DB_CHESS_CONFIG: dict`, `app.database.engine_chess: Engine`, `"chess"` key in `app.database.engines: dict[str, Engine]`, `_RoutingSession` now routes any model with `__bind_key__ == "chess"` to `engine_chess`

- [ ] **Step 1: Add pytest to requirements.txt**

Append to the end of `requirements.txt`:

```
# Testing
pytest==8.3.4
```

Run: `pip install pytest==8.3.4`
Expected: pytest installs successfully.

- [ ] **Step 2: Write the failing test**

Create `tests/chess/test_db_config.py`:

```python
from config.db import DB_BASE_CONFIG, DB_CHESS_CONFIG


def test_chess_db_config_has_dedicated_database_name():
    assert DB_CHESS_CONFIG["database"] == "chess"


def test_chess_db_config_falls_back_to_base_host_and_user():
    assert DB_CHESS_CONFIG["host"] == DB_BASE_CONFIG["host"]
    assert DB_CHESS_CONFIG["user"] == DB_BASE_CONFIG["user"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/chess/test_db_config.py -v`
Expected: FAIL with `ImportError: cannot import name 'DB_CHESS_CONFIG' from 'config.db'`

- [ ] **Step 4: Add DB_CHESS_CONFIG to config/db.py**

In `config/db.py`, after the existing `DB_PDD_CONFIG = DB_BASE_CONFIG | {...}` block, add:

```python
DB_CHESS_CONFIG = DB_BASE_CONFIG | {
    "host": os.environ.get("CHESS_DB_HOST", DB_BASE_CONFIG["host"]),
    "user": os.environ.get("CHESS_DB_USER", DB_BASE_CONFIG["user"]),
    "password": os.environ.get("CHESS_DB_PASSWORD", DB_BASE_CONFIG["password"]),
    "port": int(os.environ.get("CHESS_DB_PORT", DB_BASE_CONFIG["port"])),
    "database": os.environ.get("CHESS_DB_DATABASE", "chess"),
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/chess/test_db_config.py -v`
Expected: 2 passed

- [ ] **Step 6: Write the engine-wiring test**

Append to `tests/chess/test_db_config.py`:

```python
def test_chess_engine_is_registered():
    from sqlalchemy.engine import Engine

    from app.database import engines

    assert "chess" in engines
    assert isinstance(engines["chess"], Engine)
```

- [ ] **Step 7: Run test to verify it fails**

Run: `python3 -m pytest tests/chess/test_db_config.py::test_chess_engine_is_registered -v`
Expected: FAIL with `KeyError` or `AssertionError` (no "chess" key in `engines` yet)

- [ ] **Step 8: Wire engine_chess into app/database.py**

In `app/database.py`, change the import line:

```python
from config.db import DB_EN_CONFIG, DB_PDD_CONFIG
```

to:

```python
from config.db import DB_CHESS_CONFIG, DB_EN_CONFIG, DB_PDD_CONFIG
```

After the `_pdd_mysql_url = (...)` block, add:

```python
_chess_mysql_url = (
    f"mysql+pymysql://{DB_CHESS_CONFIG['user']}:{DB_CHESS_CONFIG['password']}"
    f"@{DB_CHESS_CONFIG['host']}:{DB_CHESS_CONFIG['port']}/{DB_CHESS_CONFIG['database']}"
    f"?charset={DB_CHESS_CONFIG.get('charset', 'utf8mb4')}"
)
```

After the `engine_pdd: Engine = create_engine(...)` block, add:

```python
engine_chess: Engine = create_engine(
    _chess_mysql_url,
    pool_size=50,
    max_overflow=200,
    pool_recycle=3600,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)
```

Change:

```python
engines: dict[str, Engine] = {"en": engine_en, "pdd": engine_pdd}
```

to:

```python
engines: dict[str, Engine] = {"en": engine_en, "pdd": engine_pdd, "chess": engine_chess}
```

In `_RoutingSession.get_bind`, change:

```python
class _RoutingSession(Session):
    def get_bind(self, mapper=None, clause=None):
        if mapper is not None:
            bind_key = getattr(mapper.class_, "__bind_key__", None)
            if bind_key == "pdd":
                return engine_pdd
        return engine_en
```

to:

```python
class _RoutingSession(Session):
    def get_bind(self, mapper=None, clause=None):
        if mapper is not None:
            bind_key = getattr(mapper.class_, "__bind_key__", None)
            if bind_key == "pdd":
                return engine_pdd
            if bind_key == "chess":
                return engine_chess
        return engine_en
```

- [ ] **Step 9: Run test to verify it passes**

Run: `python3 -m pytest tests/chess/test_db_config.py -v`
Expected: 3 passed

- [ ] **Step 10: Add CHESS_DB_* env vars to .env.example**

Append to `.env.example`:

```
# Chess 模块（独立数据库，缺省本机同账号 / 库名 chess）
CHESS_DB_HOST=localhost
CHESS_DB_USER=root
CHESS_DB_PASSWORD=
CHESS_DB_DATABASE=chess
```

- [ ] **Step 11: Commit**

```bash
git add requirements.txt config/db.py app/database.py .env.example tests/chess/test_db_config.py
git commit -m "feat: add dedicated chess database config and engine"
```

---

### Task 2: Chess SQLAlchemy models

**Files:**
- Create: `model/chess/__init__.py`
- Create: `model/chess/player.py`
- Create: `model/chess/session.py`
- Create: `model/chess/room.py`
- Create: `model/chess/move.py`
- Create: `model/chess/queue_entry.py`
- Create: `tests/chess/__init__.py` (empty, makes `tests/chess` a package so `conftest.py` fixtures scope correctly)
- Create: `tests/chess/conftest.py`
- Test: `tests/chess/test_models.py`

**Interfaces:**
- Consumes: `app.app.Base` (declarative base), `model.common.base_model.BaseModel`
- Produces: `ChessPlayer(id, open_id, nickname, avatar_url)`, `ChessSession(id, token, player_id, expires_at)`, `ChessRoom(id, red_player_id, black_player_id, fen, turn, status)`, `ChessMove(id, room_id, seq, color, from_row, from_col, to_row, to_col, piece, captured, iccs)`, `ChessQueueEntry(id, player_id, joined_at)` — all importable from `model.chess`. Test fixture `chess_db` (in `tests/chess/conftest.py`) sets up an in-memory SQLite session usable by any test under `tests/chess/`.

- [ ] **Step 1: Create the model files**

Create `model/chess/player.py`:

```python
# model/chess/player.py
"""
棋手模型 - chess 数据库
"""
from sqlalchemy import Column, String

from app.app import Base
from model.common.base_model import BaseModel


class ChessPlayer(Base, BaseModel):
    __tablename__ = "chess_players"
    __bind_key__ = "chess"

    open_id = Column(String(100), nullable=False, comment="登录标识（mock 微信 code 派生）")
    nickname = Column(String(100), nullable=False, comment="昵称")
    avatar_url = Column(String(500), nullable=True, comment="头像地址")
```

Create `model/chess/session.py`:

```python
# model/chess/session.py
"""
登录会话模型 - chess 数据库
"""
from sqlalchemy import Column, DateTime, Integer, String

from app.app import Base
from model.common.base_model import BaseModel


class ChessSession(Base, BaseModel):
    __tablename__ = "chess_sessions"
    __bind_key__ = "chess"

    token = Column(String(36), nullable=False, unique=True, comment="会话令牌")
    player_id = Column(Integer, nullable=False, comment="棋手 ID")
    expires_at = Column(DateTime(), nullable=False, comment="过期时间")
```

Create `model/chess/room.py`:

```python
# model/chess/room.py
"""
对局房间模型 - chess 数据库
"""
from sqlalchemy import Column, Integer, String

from app.app import Base
from model.common.base_model import BaseModel


class ChessRoom(Base, BaseModel):
    __tablename__ = "chess_rooms"
    __bind_key__ = "chess"

    red_player_id = Column(Integer, nullable=False, comment="红方棋手 ID")
    black_player_id = Column(Integer, nullable=False, comment="黑方棋手 ID")
    fen = Column(String(200), nullable=False, comment="当前局面（含轮走方）")
    turn = Column(String(10), nullable=False, comment="轮走方：red/black")
    status = Column(String(20), nullable=False, comment="对局状态")
```

Create `model/chess/move.py`:

```python
# model/chess/move.py
"""
着法记录模型 - chess 数据库
"""
from sqlalchemy import Column, Integer, String

from app.app import Base
from model.common.base_model import BaseModel


class ChessMove(Base, BaseModel):
    __tablename__ = "chess_moves"
    __bind_key__ = "chess"

    room_id = Column(Integer, nullable=False, comment="所属房间 ID")
    seq = Column(Integer, nullable=False, comment="着法序号，从 1 开始")
    color = Column(String(10), nullable=False, comment="走子方：red/black")
    from_row = Column(Integer, nullable=False)
    from_col = Column(Integer, nullable=False)
    to_row = Column(Integer, nullable=False)
    to_col = Column(Integer, nullable=False)
    piece = Column(String(20), nullable=False, comment="棋子类型")
    captured = Column(String(20), nullable=True, comment="被吃棋子类型")
    iccs = Column(String(10), nullable=False, comment="ICCS 记谱")
```

Create `model/chess/queue_entry.py`:

```python
# model/chess/queue_entry.py
"""
匹配队列模型 - chess 数据库
"""
from sqlalchemy import Column, DateTime, Integer

from app.app import Base
from model.common.base_model import BaseModel


class ChessQueueEntry(Base, BaseModel):
    __tablename__ = "chess_queue_entries"
    __bind_key__ = "chess"

    player_id = Column(Integer, nullable=False, comment="棋手 ID")
    joined_at = Column(DateTime(), nullable=False, comment="入队时间")
```

Create `model/chess/__init__.py`:

```python
# model/chess/__init__.py
"""
Chess 模型模块
"""
from .move import ChessMove
from .player import ChessPlayer
from .queue_entry import ChessQueueEntry
from .room import ChessRoom
from .session import ChessSession

__all__ = ["ChessPlayer", "ChessSession", "ChessRoom", "ChessMove", "ChessQueueEntry"]
```

- [ ] **Step 2: Create the empty tests/chess package marker**

Create `tests/chess/__init__.py` (empty file, zero bytes).

- [ ] **Step 3: Create the SQLite test fixture**

Create `tests/chess/conftest.py`:

```python
"""
Chess 模块测试夹具：使用内存 SQLite 替代真实 MySQL。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, clear_request_session, set_request_session
from model.chess import ChessMove, ChessPlayer, ChessQueueEntry, ChessRoom, ChessSession

CHESS_TABLES = [
    ChessPlayer.__table__,
    ChessSession.__table__,
    ChessRoom.__table__,
    ChessMove.__table__,
    ChessQueueEntry.__table__,
]


@pytest.fixture
def chess_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=CHESS_TABLES)
    session = sessionmaker(bind=engine)()
    set_request_session(session)
    try:
        yield session
    finally:
        clear_request_session()
        session.close()
        engine.dispose()
```

- [ ] **Step 4: Write the failing test**

Create `tests/chess/test_models.py`:

```python
from model.chess import ChessPlayer


def test_insert_and_get_chess_player(chess_db):
    player_id = ChessPlayer.insert({
        "open_id": "mock_123",
        "nickname": "棋友 123",
        "avatar_url": None,
    })

    player = ChessPlayer.get_by_id(player_id)

    assert player is not None
    assert player.open_id == "mock_123"
    assert player.nickname == "棋友 123"
```

- [ ] **Step 5: Run test to verify it fails**

Run: `python3 -m pytest tests/chess/test_models.py -v`
Expected: FAIL — before this step the model files did not exist, or the fixture/table wasn't wired; after Steps 1-3 above are in place this should actually already pass. If it passes immediately, skip to Step 6 without changes (this can happen when a task's setup and test land in the same pass) — do not force an artificial failure.

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 -m pytest tests/chess/test_models.py -v`
Expected: 1 passed

- [ ] **Step 7: Commit**

```bash
git add model/chess tests/chess/__init__.py tests/chess/conftest.py tests/chess/test_models.py
git commit -m "feat: add chess SQLAlchemy models and sqlite test fixture"
```

---

### Task 3: Rules engine — board representation, FEN, ICCS conversion

**Files:**
- Create: `service/chess/__init__.py`
- Create: `service/chess/rules.py`
- Test: `tests/chess/test_rules.py`

**Interfaces:**
- Consumes: nothing (pure Python, no DB/FastAPI)
- Produces: `Position(row: int, col: int)`, `Piece(color: Color, type: PieceType)`, `MoveResult(color, from_, to, piece, captured, iccs)`, `GameSnapshot(board, turn, status, history, fen)`, `position_to_iccs(Position) -> str`, `iccs_to_position(str) -> Position`, `initial_board() -> list[list[Piece|None]]`, `encode_fen(board, turn) -> str`, `decode_fen(fen) -> tuple[board, turn]`. Later tasks (4, 5) append to this same file and consume these names directly.

- [ ] **Step 1: Write the failing tests**

Create `service/chess/__init__.py`:

```python
# service/chess/__init__.py
"""
Chess 服务模块
"""
```

Create `tests/chess/test_rules.py`:

```python
from service.chess import rules


def test_initial_snapshot_turn_is_red():
    snapshot = rules.create_initial_snapshot()
    assert snapshot.turn == "red"


def test_initial_snapshot_has_32_pieces():
    snapshot = rules.create_initial_snapshot()
    piece_count = sum(1 for row in snapshot.board for cell in row if cell is not None)
    assert piece_count == 32


def test_initial_snapshot_piece_placement():
    snapshot = rules.create_initial_snapshot()
    assert snapshot.board[0][0] == rules.Piece("black", "chariot")
    assert snapshot.board[9][4] == rules.Piece("red", "king")


def test_iccs_conversion_roundtrip():
    assert rules.position_to_iccs(rules.Position(0, 0)) == "a9"
    assert rules.position_to_iccs(rules.Position(9, 0)) == "a0"
    assert rules.iccs_to_position("a9") == rules.Position(0, 0)


def test_fen_roundtrip():
    board = rules.initial_board()
    fen = rules.encode_fen(board, "red")
    decoded_board, decoded_turn = rules.decode_fen(fen)
    assert decoded_board == board
    assert decoded_turn == "red"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/chess/test_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'service.chess.rules'` (`create_initial_snapshot` doesn't exist yet — note: `create_initial_snapshot` itself needs move-generation/status logic from Task 5, so for now stub `_status_after` to always return `"playing"`; Task 5 replaces the stub)

- [ ] **Step 3: Implement board representation, FEN, and ICCS conversion**

Create `service/chess/rules.py`:

```python
# service/chess/rules.py
"""
象棋（Xiangqi）规则引擎：棋盘表示、FEN 序列化、ICCS 坐标转换。
纯 Python 实现，不依赖数据库或 FastAPI，可独立单元测试。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Color = Literal["red", "black"]
PieceType = Literal["king", "advisor", "elephant", "horse", "chariot", "cannon", "soldier"]
GameStatus = Literal["playing", "check", "checkmate", "draw", "stalemate"]

PIECE_LETTERS: dict[PieceType, str] = {
    "king": "k",
    "advisor": "a",
    "elephant": "b",
    "horse": "n",
    "chariot": "r",
    "cannon": "c",
    "soldier": "p",
}
LETTER_TO_PIECE_TYPE: dict[str, PieceType] = {v: k for k, v in PIECE_LETTERS.items()}

BOARD_ROWS = 10
BOARD_COLS = 9

INITIAL_LAYOUT: list[str] = [
    "rnbakabnr",
    ".........",
    ".c.....c.",
    "p.p.p.p.p",
    ".........",
    ".........",
    "P.P.P.P.P",
    ".C.....C.",
    ".........",
    "RNBAKABNR",
]

PALACE_COLS = {3, 4, 5}
BLACK_PALACE_ROWS = {0, 1, 2}
RED_PALACE_ROWS = {7, 8, 9}


@dataclass(frozen=True)
class Position:
    row: int
    col: int


@dataclass(frozen=True)
class Piece:
    color: Color
    type: PieceType


@dataclass(frozen=True)
class MoveResult:
    color: Color
    from_: Position
    to: Position
    piece: PieceType
    captured: Optional[PieceType]
    iccs: str


@dataclass
class GameSnapshot:
    board: list
    turn: Color
    status: GameStatus
    history: list
    fen: str


def position_to_iccs(position: Position) -> str:
    return f"{chr(97 + position.col)}{9 - position.row}"


def iccs_to_position(square: str) -> Position:
    return Position(row=9 - int(square[1]), col=ord(square[0]) - 97)


def _letter_to_piece(letter: str) -> Piece:
    color: Color = "red" if letter.isupper() else "black"
    return Piece(color=color, type=LETTER_TO_PIECE_TYPE[letter.lower()])


def _piece_to_letter(piece: Piece) -> str:
    letter = PIECE_LETTERS[piece.type]
    return letter.upper() if piece.color == "red" else letter


def _empty_board() -> list:
    return [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]


def board_from_rows(rows: list) -> list:
    board = _empty_board()
    for row_index, row in enumerate(rows):
        for col_index, char in enumerate(row):
            if char != ".":
                board[row_index][col_index] = _letter_to_piece(char)
    return board


def initial_board() -> list:
    return board_from_rows(INITIAL_LAYOUT)


def board_to_fen_rows(board: list) -> str:
    rows_str = []
    for row in board:
        parts = []
        empty_run = 0
        for cell in row:
            if cell is None:
                empty_run += 1
            else:
                if empty_run:
                    parts.append(str(empty_run))
                    empty_run = 0
                parts.append(_piece_to_letter(cell))
        if empty_run:
            parts.append(str(empty_run))
        rows_str.append("".join(parts))
    return "/".join(rows_str)


def encode_fen(board: list, turn: Color) -> str:
    turn_char = "r" if turn == "red" else "b"
    return f"{board_to_fen_rows(board)} {turn_char}"


def decode_fen(fen: str):
    board_part, turn_part = fen.split(" ")
    board = _empty_board()
    for row_index, row_str in enumerate(board_part.split("/")):
        col_index = 0
        for char in row_str:
            if char.isdigit():
                col_index += int(char)
            else:
                board[row_index][col_index] = _letter_to_piece(char)
                col_index += 1
    turn: Color = "red" if turn_part == "r" else "black"
    return board, turn


def _status_after(board: list, turn: Color) -> GameStatus:
    # Interim stub: Task 5 replaces this with real check/checkmate/stalemate/draw
    # detection. Until then every position reports "playing".
    return "playing"


def create_initial_snapshot() -> GameSnapshot:
    board = initial_board()
    turn: Color = "red"
    fen = encode_fen(board, turn)
    return GameSnapshot(board=board, turn=turn, status=_status_after(board, turn), history=[], fen=fen)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/chess/test_rules.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add service/chess/__init__.py service/chess/rules.py tests/chess/test_rules.py
git commit -m "feat: add chess rules engine board/FEN/ICCS representation"
```

---

### Task 4: Rules engine — piece movement generation

**Files:**
- Modify: `service/chess/rules.py`
- Modify: `tests/chess/test_rules.py`

**Interfaces:**
- Consumes: `Position`, `Piece`, `Color`, `PieceType`, board list-of-lists from Task 3
- Produces: `_pseudo_moves_for(board, pos: Position) -> list[Position]` — pseudo-legal moves for the piece at `pos`, ignoring whether the move leaves the mover's own king in check (that filter is added in Task 5). Task 5 consumes this function directly.

- [ ] **Step 1: Write the failing tests**

Append to `tests/chess/test_rules.py`:

```python
def test_soldier_before_river_moves_forward_only():
    board = rules.board_from_rows([
        ".........", ".........", ".........", ".........", ".........",
        ".........", "....P....", ".........", ".........", "K........",
    ])
    moves = set(rules._pseudo_moves_for(board, rules.Position(6, 4)))
    assert moves == {rules.Position(5, 4)}


def test_soldier_after_crossing_river_gains_sideways_moves():
    board = rules.board_from_rows([
        ".........", ".........", ".........", ".........", "....P....",
        ".........", ".........", ".........", ".........", "K........",
    ])
    moves = set(rules._pseudo_moves_for(board, rules.Position(4, 4)))
    assert moves == {rules.Position(3, 4), rules.Position(4, 3), rules.Position(4, 5)}


def test_elephant_cannot_cross_river():
    board = rules.board_from_rows([
        ".........", ".........", ".........", ".........", ".........",
        ".........", "..B......", ".........", ".........", "K........",
    ])
    moves = set(rules._pseudo_moves_for(board, rules.Position(6, 2)))
    assert moves == {rules.Position(8, 0), rules.Position(8, 4)}


def test_elephant_blocked_by_eye():
    board = rules.board_from_rows([
        ".........", ".........", ".........", ".........", ".........",
        ".........", "..B......", ".p.......", ".........", "K........",
    ])
    moves = set(rules._pseudo_moves_for(board, rules.Position(6, 2)))
    assert rules.Position(8, 0) not in moves
    assert rules.Position(8, 4) in moves


def test_horse_free_movement_has_8_options():
    board = rules.board_from_rows([
        ".........", ".........", ".........", ".........", ".........",
        ".........", "..N......", ".........", ".........", "K........",
    ])
    moves = set(rules._pseudo_moves_for(board, rules.Position(6, 2)))
    assert len(moves) == 8


def test_horse_blocked_by_leg():
    board = rules.board_from_rows([
        ".........", ".........", ".........", ".........", ".........",
        "..p......", "..N......", ".........", ".........", "K........",
    ])
    moves = set(rules._pseudo_moves_for(board, rules.Position(6, 2)))
    assert rules.Position(4, 1) not in moves
    assert rules.Position(4, 3) not in moves
    assert len(moves) == 6


def test_cannon_cannot_capture_without_a_screen():
    board = rules.board_from_rows([
        ".........", ".........", ".........", ".........", ".........",
        ".........", "..C..p...", ".........", ".........", "K........",
    ])
    moves = set(rules._pseudo_moves_for(board, rules.Position(6, 2)))
    assert rules.Position(6, 5) not in moves


def test_cannon_captures_with_exactly_one_screen():
    board = rules.board_from_rows([
        ".........", ".........", ".........", ".........", ".........",
        ".........", "..C.n.p..", ".........", ".........", "K........",
    ])
    moves = set(rules._pseudo_moves_for(board, rules.Position(6, 2)))
    assert rules.Position(6, 6) in moves
    assert rules.Position(6, 4) not in moves


def test_chariot_stops_at_first_blocker():
    board = rules.board_from_rows([
        ".........", ".........", ".........", ".........", ".........",
        ".........", "..R..p...", ".........", ".........", "K........",
    ])
    moves = set(rules._pseudo_moves_for(board, rules.Position(6, 2)))
    assert rules.Position(6, 5) in moves
    assert rules.Position(6, 6) not in moves
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/chess/test_rules.py -v`
Expected: FAIL with `AttributeError: module 'service.chess.rules' has no attribute '_pseudo_moves_for'`

- [ ] **Step 3: Implement piece movement generation**

Append to `service/chess/rules.py`:

```python
def _in_bounds(row: int, col: int) -> bool:
    return 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS


def _in_palace(row: int, col: int, color: Color) -> bool:
    if col not in PALACE_COLS:
        return False
    return row in BLACK_PALACE_ROWS if color == "black" else row in RED_PALACE_ROWS


def _on_own_side(row: int, color: Color) -> bool:
    return row <= 4 if color == "black" else row >= 5


def _king_moves(board, pos: Position, color: Color) -> list:
    moves = []
    for d_row, d_col in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        row, col = pos.row + d_row, pos.col + d_col
        if _in_bounds(row, col) and _in_palace(row, col, color):
            target = board[row][col]
            if target is None or target.color != color:
                moves.append(Position(row=row, col=col))
    return moves


def _advisor_moves(board, pos: Position, color: Color) -> list:
    moves = []
    for d_row, d_col in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        row, col = pos.row + d_row, pos.col + d_col
        if _in_bounds(row, col) and _in_palace(row, col, color):
            target = board[row][col]
            if target is None or target.color != color:
                moves.append(Position(row=row, col=col))
    return moves


def _elephant_moves(board, pos: Position, color: Color) -> list:
    moves = []
    for d_row, d_col in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
        row, col = pos.row + d_row, pos.col + d_col
        eye_row, eye_col = pos.row + d_row // 2, pos.col + d_col // 2
        if not _in_bounds(row, col) or not _on_own_side(row, color):
            continue
        if board[eye_row][eye_col] is not None:
            continue
        target = board[row][col]
        if target is None or target.color != color:
            moves.append(Position(row=row, col=col))
    return moves


def _horse_moves(board, pos: Position, color: Color) -> list:
    moves = []
    steps = [
        (-2, -1, -1, 0), (-2, 1, -1, 0),
        (2, -1, 1, 0), (2, 1, 1, 0),
        (-1, -2, 0, -1), (1, -2, 0, -1),
        (-1, 2, 0, 1), (1, 2, 0, 1),
    ]
    for d_row, d_col, leg_row, leg_col in steps:
        row, col = pos.row + d_row, pos.col + d_col
        leg_r, leg_c = pos.row + leg_row, pos.col + leg_col
        if not _in_bounds(row, col):
            continue
        if board[leg_r][leg_c] is not None:
            continue
        target = board[row][col]
        if target is None or target.color != color:
            moves.append(Position(row=row, col=col))
    return moves


def _sliding_moves(board, pos: Position, color: Color, directions) -> list:
    moves = []
    for d_row, d_col in directions:
        row, col = pos.row + d_row, pos.col + d_col
        while _in_bounds(row, col):
            target = board[row][col]
            if target is None:
                moves.append(Position(row=row, col=col))
            else:
                if target.color != color:
                    moves.append(Position(row=row, col=col))
                break
            row += d_row
            col += d_col
    return moves


def _chariot_moves(board, pos: Position, color: Color) -> list:
    return _sliding_moves(board, pos, color, [(-1, 0), (1, 0), (0, -1), (0, 1)])


def _cannon_moves(board, pos: Position, color: Color) -> list:
    moves = []
    for d_row, d_col in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        row, col = pos.row + d_row, pos.col + d_col
        screen_found = False
        while _in_bounds(row, col):
            target = board[row][col]
            if not screen_found:
                if target is None:
                    moves.append(Position(row=row, col=col))
                else:
                    screen_found = True
            else:
                if target is not None:
                    if target.color != color:
                        moves.append(Position(row=row, col=col))
                    break
            row += d_row
            col += d_col
    return moves


def _soldier_moves(board, pos: Position, color: Color) -> list:
    moves = []
    forward = 1 if color == "black" else -1
    crossed = pos.row >= 5 if color == "black" else pos.row <= 4
    candidates = [(forward, 0)]
    if crossed:
        candidates += [(0, -1), (0, 1)]
    for d_row, d_col in candidates:
        row, col = pos.row + d_row, pos.col + d_col
        if _in_bounds(row, col):
            target = board[row][col]
            if target is None or target.color != color:
                moves.append(Position(row=row, col=col))
    return moves


_PSEUDO_MOVE_GENERATORS = {
    "king": _king_moves,
    "advisor": _advisor_moves,
    "elephant": _elephant_moves,
    "horse": _horse_moves,
    "chariot": _chariot_moves,
    "cannon": _cannon_moves,
    "soldier": _soldier_moves,
}


def _pseudo_moves_for(board, pos: Position) -> list:
    piece = board[pos.row][pos.col]
    if piece is None:
        return []
    return _PSEUDO_MOVE_GENERATORS[piece.type](board, pos, piece.color)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/chess/test_rules.py -v`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add service/chess/rules.py tests/chess/test_rules.py
git commit -m "feat: add per-piece pseudo-legal move generation to chess rules engine"
```

---

### Task 5: Rules engine — check detection, checkmate/stalemate/draw, move API

**Files:**
- Modify: `service/chess/rules.py`
- Modify: `tests/chess/test_rules.py`

**Interfaces:**
- Consumes: `_pseudo_moves_for` (Task 4), `Position`/`Piece`/`GameSnapshot`/`MoveResult`/`encode_fen`/`decode_fen` (Task 3)
- Produces: `legal_moves_for(board, pos) -> list[Position]`, `all_legal_moves(board, color) -> list[tuple[Position, Position]]`, `apply_move_to_fen(fen: str, from_pos: Position, to_pos: Position) -> GameSnapshot | None` — this is the main entry point `service/chess/matchmaking.py` (Task 7) will call.

- [ ] **Step 1: Write the failing tests**

Append to `tests/chess/test_rules.py`:

```python
def test_flying_general_rule_forbids_exposing_move():
    board = rules.board_from_rows([
        "....k....", ".........", ".........", ".........", "....p....",
        ".........", ".........", ".........", ".........", "....K....",
    ])
    moves = set(rules.legal_moves_for(board, rules.Position(4, 4)))
    assert rules.Position(4, 3) not in moves
    assert rules.Position(4, 5) not in moves


def test_checkmate_detection():
    board = rules.board_from_rows([
        "R...k....",
        ".........",
        "....R....",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        "....K....",
    ])
    assert rules.all_legal_moves(board, "black") == []
    assert rules._status_after(board, "black") == "checkmate"


def test_stalemate_detection():
    board = rules.board_from_rows([
        "...k.....",
        "R........",
        "....R....",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        "....K....",
    ])
    assert not rules._is_in_check(board, "black")
    assert rules.all_legal_moves(board, "black") == []
    assert rules._status_after(board, "black") == "stalemate"


def test_apply_move_to_fen_accepts_legal_move():
    initial_fen = rules.encode_fen(rules.initial_board(), "red")
    snapshot = rules.apply_move_to_fen(initial_fen, rules.Position(6, 0), rules.Position(5, 0))

    assert snapshot is not None
    assert snapshot.turn == "black"
    assert snapshot.history[0].iccs == "a3a4"


def test_apply_move_to_fen_rejects_illegal_move():
    initial_fen = rules.encode_fen(rules.initial_board(), "red")
    snapshot = rules.apply_move_to_fen(initial_fen, rules.Position(6, 0), rules.Position(3, 0))

    assert snapshot is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/chess/test_rules.py -v`
Expected: FAIL with `AttributeError: module 'service.chess.rules' has no attribute 'legal_moves_for'`

- [ ] **Step 3: Implement check detection, status detection, and the move API**

In `service/chess/rules.py`, replace the placeholder:

```python
def _status_after(board: list, turn: Color) -> GameStatus:
    # Placeholder until Task 5 adds check/checkmate/stalemate/draw detection.
    return "playing"
```

with the following (delete the placeholder, add everything below at the same location — after `_pseudo_moves_for` and before `create_initial_snapshot`):

```python
def _king_position(board, color: Color):
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            piece = board[row][col]
            if piece is not None and piece.color == color and piece.type == "king":
                return Position(row=row, col=col)
    return None


def _kings_face_each_other(board) -> bool:
    black_king = _king_position(board, "black")
    red_king = _king_position(board, "red")
    if black_king is None or red_king is None:
        return False
    if black_king.col != red_king.col:
        return False
    col = black_king.col
    for row in range(black_king.row + 1, red_king.row):
        if board[row][col] is not None:
            return False
    return True


def _is_in_check(board, color: Color) -> bool:
    king_pos = _king_position(board, color)
    if king_pos is None:
        return False
    opponent: Color = "black" if color == "red" else "red"
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            piece = board[row][col]
            if piece is not None and piece.color == opponent:
                if king_pos in _pseudo_moves_for(board, Position(row=row, col=col)):
                    return True
    return _kings_face_each_other(board)


def _apply_pseudo_move(board, from_pos: Position, to_pos: Position):
    new_board = [row[:] for row in board]
    new_board[to_pos.row][to_pos.col] = new_board[from_pos.row][from_pos.col]
    new_board[from_pos.row][from_pos.col] = None
    return new_board


def legal_moves_for(board, pos: Position) -> list:
    piece = board[pos.row][pos.col]
    if piece is None:
        return []
    legal = []
    for candidate in _pseudo_moves_for(board, pos):
        simulated = _apply_pseudo_move(board, pos, candidate)
        if not _is_in_check(simulated, piece.color):
            legal.append(candidate)
    return legal


def all_legal_moves(board, color: Color) -> list:
    moves = []
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            piece = board[row][col]
            if piece is not None and piece.color == color:
                origin = Position(row=row, col=col)
                for target in legal_moves_for(board, origin):
                    moves.append((origin, target))
    return moves


def _is_bare_kings(board) -> bool:
    for row in board:
        for piece in row:
            if piece is not None and piece.type != "king":
                return False
    return True


def _status_after(board: list, turn: Color) -> GameStatus:
    if _is_bare_kings(board):
        return "draw"
    in_check = _is_in_check(board, turn)
    has_moves = bool(all_legal_moves(board, turn))
    if in_check and not has_moves:
        return "checkmate"
    if in_check:
        return "check"
    if not has_moves:
        return "stalemate"
    return "playing"


def _move_piece(board, from_pos: Position, to_pos: Position, color: Color):
    piece = board[from_pos.row][from_pos.col]
    if piece is None or piece.color != color:
        return None
    if to_pos not in legal_moves_for(board, from_pos):
        return None
    captured_piece = board[to_pos.row][to_pos.col]
    board[to_pos.row][to_pos.col] = piece
    board[from_pos.row][from_pos.col] = None
    return MoveResult(
        color=color,
        from_=from_pos,
        to=to_pos,
        piece=piece.type,
        captured=captured_piece.type if captured_piece else None,
        iccs=f"{position_to_iccs(from_pos)}{position_to_iccs(to_pos)}",
    )


def apply_move_to_fen(fen: str, from_pos: Position, to_pos: Position):
    board, turn = decode_fen(fen)
    move_result = _move_piece(board, from_pos, to_pos, turn)
    if move_result is None:
        return None
    next_turn: Color = "black" if turn == "red" else "red"
    new_fen = encode_fen(board, next_turn)
    return GameSnapshot(
        board=board,
        turn=next_turn,
        status=_status_after(board, next_turn),
        history=[move_result],
        fen=new_fen,
    )
```

Note: `_status_after` is defined twice in the source at this point (the old placeholder and the new one) only if Step 3 is done as a literal append — to avoid that, this step **replaces** the placeholder in place rather than appending after it. Double-check there is exactly one `_status_after` definition left in the file before moving on.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/chess/test_rules.py -v`
Expected: 19 passed

- [ ] **Step 5: Known limitation — note it in a comment**

Add this comment directly above the `_is_bare_kings` function in `service/chess/rules.py`:

```python
# Draw detection only covers the bare-kings endgame. Perpetual-check/perpetual-chase
# repetition rules (as implemented by xiangqi.js) are not reimplemented here.
```

- [ ] **Step 6: Commit**

```bash
git add service/chess/rules.py tests/chess/test_rules.py
git commit -m "feat: add check/checkmate/stalemate detection and move API to chess rules engine"
```

---

### Task 6: Auth service — mock WeChat login and session verification

**Files:**
- Create: `service/chess/auth.py`
- Test: `tests/chess/test_auth.py`

**Interfaces:**
- Consumes: `model.chess.ChessPlayer`, `model.chess.ChessSession` (Task 2), `app.app.db`, `app.errors.unexpected_error_response`
- Produces: `login_with_wechat_code(code: str) -> dict`, `require_session(token: str) -> ChessSession | None`, `get_player(player_id: int) -> ChessPlayer | None` — consumed by `routes/chess.py` (Task 8)

- [ ] **Step 1: Write the failing tests**

Create `tests/chess/test_auth.py`:

```python
from service.chess import auth


def test_login_creates_player_and_session(chess_db):
    result = auth.login_with_wechat_code("wx-login-42")

    assert result["code"] == 200
    assert result["data"]["player"]["nickname"] == "棋友 42"
    assert result["data"]["session"]["token"]


def test_login_is_idempotent_for_same_code(chess_db):
    first = auth.login_with_wechat_code("wx-login-42")
    second = auth.login_with_wechat_code("wx-login-42")

    assert first["data"]["player"]["id"] == second["data"]["player"]["id"]
    assert first["data"]["session"]["token"] != second["data"]["session"]["token"]


def test_login_rejects_empty_code(chess_db):
    result = auth.login_with_wechat_code("   ")

    assert result["code"] == 400


def test_require_session_returns_none_for_unknown_token(chess_db):
    assert auth.require_session("does-not-exist") is None


def test_require_session_returns_session_for_valid_token(chess_db):
    login_result = auth.login_with_wechat_code("wx-login-7")
    token = login_result["data"]["session"]["token"]

    session = auth.require_session(token)

    assert session is not None
    assert session.token == token


def test_require_session_rejects_expired_token(chess_db, monkeypatch):
    import datetime as dt

    from service.chess import auth as auth_module

    login_result = auth.login_with_wechat_code("wx-login-99")
    token = login_result["data"]["session"]["token"]

    future = dt.datetime.now() + dt.timedelta(days=8)

    class _FrozenDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return future

    monkeypatch.setattr(auth_module, "datetime", _FrozenDateTime)

    assert auth.require_session(token) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/chess/test_auth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'service.chess.auth'`

- [ ] **Step 3: Implement the auth service**

Create `service/chess/auth.py`:

```python
# service/chess/auth.py
"""
Chess 登录服务：mock 微信登录 + 会话签发/校验
"""
import hashlib
import re
import uuid
from datetime import datetime, timedelta

from app.app import db
from app.errors import unexpected_error_response
from model.chess import ChessPlayer, ChessSession

SESSION_TTL = timedelta(days=7)


def _mock_open_id(code: str) -> str:
    return f"mock_{code}"


def _mock_nickname(code: str) -> str:
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    match = re.search(r"(\d+)$", code)
    suffix = match.group(1) if match else str(int(digest[:4], 16) % 10000 or 1)
    return f"棋友 {suffix}"


def login_with_wechat_code(code: str) -> dict:
    """mock 微信登录：同一 code 始终对应同一棋手，每次登录签发新会话"""
    trimmed_code = (code or "").strip()
    if not trimmed_code:
        return {"code": 400, "msg": "微信登录 code 不能为空"}

    try:
        open_id = _mock_open_id(trimmed_code)
        player = ChessPlayer.select_one_by({"open_id": open_id})
        if player is None:
            player_id = ChessPlayer.insert({
                "open_id": open_id,
                "nickname": _mock_nickname(trimmed_code),
            })
            player = ChessPlayer.get_by_id(player_id)

        expires_at = datetime.now() + SESSION_TTL
        token = str(uuid.uuid4())
        ChessSession.insert({
            "token": token,
            "player_id": player.id,
            "expires_at": expires_at,
        })

        return {
            "code": 200,
            "data": {
                "player": {
                    "id": player.id,
                    "nickname": player.nickname,
                    "avatar_url": player.avatar_url,
                },
                "session": {
                    "token": token,
                    "player_id": player.id,
                    "expires_at": expires_at.isoformat(),
                },
            },
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def require_session(token: str):
    """校验会话令牌，过期则软删除并返回 None"""
    session = ChessSession.select_one_by({"token": token})
    if session is None:
        return None
    if session.expires_at <= datetime.now():
        ChessSession.delete(session.id)
        return None
    return session


def get_player(player_id: int):
    return ChessPlayer.get_by_id(player_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/chess/test_auth.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add service/chess/auth.py tests/chess/test_auth.py
git commit -m "feat: add chess mock-WeChat auth service"
```

---

### Task 7: Matchmaking service — queue, rooms, move submission

**Files:**
- Create: `service/chess/matchmaking.py`
- Test: `tests/chess/test_matchmaking.py`

**Interfaces:**
- Consumes: `model.chess.ChessRoom/ChessMove/ChessQueueEntry` (Task 2), `service.chess.rules.create_initial_snapshot/apply_move_to_fen/Position` (Tasks 3/5), `app.app.db`, `app.errors.unexpected_error_response`
- Produces: `join_queue(player_id: int) -> dict`, `leave_queue(player_id: int) -> dict`, `get_status(player_id: int) -> dict`, `get_room(room_id: int) -> dict`, `submit_move(room_id: int, player_id: int, from_pos: dict, to_pos: dict) -> dict` — all consumed by `routes/chess.py` (Task 8)

- [ ] **Step 1: Write the failing tests**

Create `tests/chess/test_matchmaking.py`:

```python
from service.chess import matchmaking


def test_first_player_to_join_is_queued(chess_db):
    result = matchmaking.join_queue(1)

    assert result["data"]["status"] == "queued"


def test_second_player_gets_matched_and_room_created(chess_db):
    matchmaking.join_queue(1)
    result = matchmaking.join_queue(2)

    assert result["data"]["status"] == "matched"
    room = result["data"]["room"]
    assert {room["red_player_id"], room["black_player_id"]} == {1, 2}
    assert room["turn"] == "red"
    assert room["status"] == "playing"


def test_joining_twice_stays_queued_once(chess_db):
    matchmaking.join_queue(1)
    result = matchmaking.join_queue(1)

    assert result["data"]["status"] == "queued"


def test_leave_queue_removes_entry(chess_db):
    matchmaking.join_queue(1)
    matchmaking.leave_queue(1)
    result = matchmaking.join_queue(2)

    assert result["data"]["status"] == "queued"


def test_get_status_reports_queued_then_matched(chess_db):
    matchmaking.join_queue(1)
    assert matchmaking.get_status(1)["data"]["status"] == "queued"

    matchmaking.join_queue(2)
    assert matchmaking.get_status(1)["data"]["status"] == "matched"


def test_submit_move_rejects_wrong_turn(chess_db):
    matchmaking.join_queue(1)
    matched = matchmaking.join_queue(2)
    room = matched["data"]["room"]

    result = matchmaking.submit_move(
        room["id"], room["black_player_id"], {"row": 6, "col": 0}, {"row": 5, "col": 0}
    )

    assert result["code"] == 400
    assert result["msg"] == "当前不是你的回合"


def test_submit_move_accepts_legal_move_and_records_history(chess_db):
    matchmaking.join_queue(1)
    matched = matchmaking.join_queue(2)
    room = matched["data"]["room"]

    result = matchmaking.submit_move(
        room["id"], room["red_player_id"], {"row": 6, "col": 0}, {"row": 5, "col": 0}
    )

    assert result["code"] == 200
    assert result["data"]["room"]["turn"] == "black"

    room_state = matchmaking.get_room(room["id"])
    assert len(room_state["data"]["history"]) == 1
    assert room_state["data"]["history"][0]["iccs"] == "a3a4"


def test_submit_move_rejects_illegal_move(chess_db):
    matchmaking.join_queue(1)
    matched = matchmaking.join_queue(2)
    room = matched["data"]["room"]

    result = matchmaking.submit_move(
        room["id"], room["red_player_id"], {"row": 6, "col": 0}, {"row": 3, "col": 0}
    )

    assert result["code"] == 400
    assert result["msg"] == "非法走子"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/chess/test_matchmaking.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'service.chess.matchmaking'`

- [ ] **Step 3: Implement the matchmaking service**

Create `service/chess/matchmaking.py`:

```python
# service/chess/matchmaking.py
"""
Chess 匹配与对局服务：排队、建房、提交着法、轮询状态
"""
from datetime import datetime

from app.app import db
from app.errors import unexpected_error_response
from model.chess import ChessMove, ChessQueueEntry, ChessRoom
from service.chess import rules


def _room_to_dict(room: ChessRoom) -> dict:
    return {
        "id": room.id,
        "red_player_id": room.red_player_id,
        "black_player_id": room.black_player_id,
        "fen": room.fen,
        "turn": room.turn,
        "status": room.status,
    }


def _player_color(room: ChessRoom, player_id: int):
    if room.red_player_id == player_id:
        return "red"
    if room.black_player_id == player_id:
        return "black"
    return None


def _create_room(red_player_id: int, black_player_id: int) -> ChessRoom:
    snapshot = rules.create_initial_snapshot()
    room_id = ChessRoom.insert({
        "red_player_id": red_player_id,
        "black_player_id": black_player_id,
        "fen": snapshot.fen,
        "turn": snapshot.turn,
        "status": snapshot.status,
    })
    return ChessRoom.get_by_id(room_id)


def join_queue(player_id: int) -> dict:
    """加入匹配队列；若已有等待中的对手则立即建房"""
    try:
        already_queued = ChessQueueEntry.select_one_by({"player_id": player_id})
        if already_queued is not None:
            return {"code": 200, "data": {"status": "queued"}}

        opponent_entry = ChessQueueEntry.select_one_by({"order_by": {"col": "id", "sort": "asc"}})
        if opponent_entry is None:
            ChessQueueEntry.insert({"player_id": player_id, "joined_at": datetime.now()})
            return {"code": 200, "data": {"status": "queued"}}

        ChessQueueEntry.force_delete({"id": opponent_entry.id})
        room = _create_room(opponent_entry.player_id, player_id)

        return {"code": 200, "data": {"status": "matched", "room": _room_to_dict(room)}}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def leave_queue(player_id: int) -> dict:
    try:
        ChessQueueEntry.force_delete({"player_id": player_id})
        return {"code": 200, "data": {"status": "left"}}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def get_status(player_id: int) -> dict:
    try:
        queued = ChessQueueEntry.select_one_by({"player_id": player_id})
        if queued is not None:
            return {"code": 200, "data": {"status": "queued"}}

        latest_room = ChessRoom.select_one_by({
            "red_player_id": player_id,
            "order_by": {"col": "id", "sort": "desc"},
        })
        if latest_room is None:
            latest_room = ChessRoom.select_one_by({
                "black_player_id": player_id,
                "order_by": {"col": "id", "sort": "desc"},
            })
        if latest_room is None:
            return {"code": 200, "data": {"status": "idle"}}

        return {"code": 200, "data": {"status": "matched", "room": _room_to_dict(latest_room)}}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def get_room(room_id: int) -> dict:
    try:
        room = ChessRoom.get_by_id(room_id)
        if room is None:
            return {"code": 404, "msg": "房间不存在"}

        moves = ChessMove.builder_query({
            "room_id": room_id,
            "order_by": {"col": "seq", "sort": "asc"},
        }).all()

        room_data = _room_to_dict(room)
        room_data["history"] = [
            {
                "seq": move.seq,
                "color": move.color,
                "from": {"row": move.from_row, "col": move.from_col},
                "to": {"row": move.to_row, "col": move.to_col},
                "piece": move.piece,
                "captured": move.captured,
                "iccs": move.iccs,
            }
            for move in moves
        ]
        return {"code": 200, "data": room_data}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def submit_move(room_id: int, player_id: int, from_pos: dict, to_pos: dict) -> dict:
    try:
        room = ChessRoom.get_by_id(room_id)
        if room is None:
            return {"code": 404, "msg": "房间不存在"}

        color = _player_color(room, player_id)
        if color is None:
            return {"code": 403, "msg": "你不在这个房间中", "data": {"room": _room_to_dict(room)}}

        if room.turn != color:
            return {"code": 400, "msg": "当前不是你的回合", "data": {"room": _room_to_dict(room)}}

        origin = rules.Position(row=from_pos["row"], col=from_pos["col"])
        target = rules.Position(row=to_pos["row"], col=to_pos["col"])
        snapshot = rules.apply_move_to_fen(room.fen, origin, target)
        if snapshot is None:
            return {"code": 400, "msg": "非法走子", "data": {"room": _room_to_dict(room)}}

        ChessRoom.update({
            "id": room.id,
            "fen": snapshot.fen,
            "turn": snapshot.turn,
            "status": snapshot.status,
        })

        move_result = snapshot.history[0]
        existing_move_count = ChessMove.count({"room_id": room_id})
        ChessMove.insert({
            "room_id": room_id,
            "seq": existing_move_count + 1,
            "color": move_result.color,
            "from_row": move_result.from_.row,
            "from_col": move_result.from_.col,
            "to_row": move_result.to.row,
            "to_col": move_result.to.col,
            "piece": move_result.piece,
            "captured": move_result.captured,
            "iccs": move_result.iccs,
        })

        updated_room = ChessRoom.get_by_id(room_id)
        return {"code": 200, "data": {"room": _room_to_dict(updated_room)}}
    except Exception as e:
        return unexpected_error_response(e, db.session)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/chess/test_matchmaking.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add service/chess/matchmaking.py tests/chess/test_matchmaking.py
git commit -m "feat: add chess matchmaking service"
```

---

### Task 8: Chess API routes

**Files:**
- Create: `routes/chess.py`
- Modify: `routes/__init__.py`

**Interfaces:**
- Consumes: `service.chess.auth.login_with_wechat_code/require_session` (Task 6), `service.chess.matchmaking.join_queue/leave_queue/get_status/get_room/submit_move` (Task 7), `app.response.api_response`
- Produces: FastAPI routes mounted at `/chess/*` on `api_router`

- [ ] **Step 1: Create the routes module**

Create `routes/chess.py`:

```python
# routes/chess.py
"""
Chess 模块路由
"""
from fastapi import APIRouter, Header, Request

from app.response import api_response
from service.chess.auth import login_with_wechat_code, require_session
from service.chess.matchmaking import (
    get_room,
    get_status,
    join_queue,
    leave_queue,
    submit_move,
)

router = APIRouter()


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[len("Bearer "):]


def _authenticated_player_id(authorization: str | None):
    token = _bearer_token(authorization)
    session = require_session(token) if token else None
    return session.player_id if session else None


# ---------- 登录 ----------
@router.post("/auth/wechat-login")
async def route_wechat_login(request: Request):
    body = await _body(request)
    return api_response(login_with_wechat_code(body.get("code", "")))


# ---------- 匹配 ----------
@router.post("/matchmaking/join")
async def route_matchmaking_join(authorization: str | None = Header(None)):
    player_id = _authenticated_player_id(authorization)
    if player_id is None:
        return api_response({"code": 401, "msg": "登录已失效"})
    return api_response(join_queue(player_id))


@router.post("/matchmaking/leave")
async def route_matchmaking_leave(authorization: str | None = Header(None)):
    player_id = _authenticated_player_id(authorization)
    if player_id is None:
        return api_response({"code": 401, "msg": "登录已失效"})
    return api_response(leave_queue(player_id))


@router.get("/matchmaking/status")
async def route_matchmaking_status(authorization: str | None = Header(None)):
    player_id = _authenticated_player_id(authorization)
    if player_id is None:
        return api_response({"code": 401, "msg": "登录已失效"})
    return api_response(get_status(player_id))


# ---------- 房间 ----------
@router.get("/rooms/{room_id}")
async def route_room_get(room_id: int):
    return api_response(get_room(room_id))


@router.post("/rooms/{room_id}/move")
async def route_room_move(room_id: int, request: Request, authorization: str | None = Header(None)):
    player_id = _authenticated_player_id(authorization)
    if player_id is None:
        return api_response({"code": 401, "msg": "登录已失效"})

    body = await _body(request)
    return api_response(
        submit_move(room_id, player_id, body.get("from", {}), body.get("to", {}))
    )
```

- [ ] **Step 2: Mount the chess router**

In `routes/__init__.py`, change:

```python
from routes.english import router as english_router
from routes.peach import router as peach_router
```

to:

```python
from routes.chess import router as chess_router
from routes.english import router as english_router
from routes.peach import router as peach_router
```

and change:

```python
api_router.include_router(english_router, prefix="/english", tags=["english"])
api_router.include_router(peach_router, prefix="/peach", tags=["peach"])
```

to:

```python
api_router.include_router(chess_router, prefix="/chess", tags=["chess"])
api_router.include_router(english_router, prefix="/english", tags=["english"])
api_router.include_router(peach_router, prefix="/peach", tags=["peach"])
```

- [ ] **Step 3: Verify the routes are registered**

Run:

```bash
python3 -c "from app.app import app; print(sorted(r.path for r in app.routes if r.path.startswith('/chess')))"
```

Expected output:

```
['/chess/auth/wechat-login', '/chess/matchmaking/join', '/chess/matchmaking/leave', '/chess/matchmaking/status', '/chess/rooms/{room_id}', '/chess/rooms/{room_id}/move']
```

This only checks route registration (no request is made, so no live `chess` MySQL database is needed). Exercising a full request end-to-end requires either a running `chess` MySQL database matching `CHESS_DB_*` in `.env`, or overriding `get_db` with the same SQLite fixture pattern used in `tests/chess/conftest.py` — out of scope for this plan since the spec calls only for service-layer automated tests.

- [ ] **Step 4: Run the full chess test suite one more time**

Run: `python3 -m pytest tests/chess/ -v`
Expected: all tests across `test_db_config.py`, `test_models.py`, `test_rules.py`, `test_auth.py`, `test_matchmaking.py` pass (37 passed total: 3 + 1 + 19 + 6 + 8 — reconcile this count against actual collected test count and adjust if a step above changed it).

- [ ] **Step 5: Commit**

```bash
git add routes/chess.py routes/__init__.py
git commit -m "feat: mount chess API routes"
```

---

## Follow-up (not part of this plan)

- Provisioning the actual `chess` MySQL database/schema in each environment (this plan only wires config — table creation via `Base.metadata.create_all` or a migration tool is not addressed).
- A real WeChat login integration to replace the mock (out of scope per the design doc).
- Any client (web/mini-program) that consumes this API.
