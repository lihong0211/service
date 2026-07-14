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


def create_initial_snapshot() -> GameSnapshot:
    board = initial_board()
    turn: Color = "red"
    fen = encode_fen(board, turn)
    return GameSnapshot(board=board, turn=turn, status=_status_after(board, turn), history=[], fen=fen)
