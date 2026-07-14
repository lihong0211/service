# Chess module design

Date: 2026-07-15

## Context

`chess-server/` is a standalone Node/TypeScript app (Express + `ws`) implementing
Xiangqi (Chinese chess): a rules engine (`domain/rules.ts`, backed by the
`xiangqi.js` npm package), mock WeChat auth (`domain/auth.ts`), in-memory
matchmaking/rooms (`domain/matchmaking.ts`), and an HTTP+WebSocket layer
(`http/app.ts`, `http/server.ts`). It is not part of the Python app and has
its own `package.json`.

This task ports that functionality into a new `chess` module inside the
existing Python (FastAPI) app, following the same `routes/ -> service/ ->
model/` layering already used by the `english` and `peach` modules.

Two constraints shaped the design, both raised and confirmed with the user
before writing this spec:

1. **No mature Python Xiangqi rules library exists.** The closest PyPI hits
   (`xiangqi`, `gym-xiangqi`) are RL-environment wrappers, not FEN/legal-move
   engines, and are largely unmaintained. The rules engine (move legality,
   check/checkmate/stalemate/draw detection) will be reimplemented natively
   in Python rather than adopting a dependency.
2. **Production runs `uvicorn --workers 4`** (per README). chess-server's
   in-memory `Map`-based sessions/queue/rooms/sockets would break across
   worker processes. State is persisted to MySQL instead, and there is no
   WebSocket layer — clients poll REST endpoints for updates.

## Architecture

```
routes/chess.py              REST endpoints, mounted at /chess
service/chess/
  rules.py                   Pure-Python Xiangqi engine — no DB, no FastAPI import
  auth.py                    Mock WeChat login, session issue/verify (DB-backed)
  matchmaking.py             Queue + room lifecycle, move submission (DB-backed)
model/chess/
  player.py, session.py, room.py, move.py, queue_entry.py
config/db.py                 + DB_CHESS_CONFIG
app/database.py              + engine_chess, bind_key="chess" routing
```

`service/chess/rules.py` has no framework or database dependency, so it is
directly unit-testable in isolation, matching how `xiangqi.js` is
engine-only in chess-server.

Because there is no WebSocket push, matchmaking needs one endpoint beyond
chess-server's surface: a "did I get matched yet" status check. Without a
push, the player left waiting in the queue has no other way to learn a room
was created for them.

## Data model

New dedicated `chess` MySQL database (own `DB_CHESS_CONFIG`, own env vars,
own engine — mirrors how `DB_EN_CONFIG`/`DB_PDD_CONFIG` are separate today).
All tables use the project's existing `BaseModel` (soft delete via
`deleted_at`, `insert`/`update`/`builder_query` conventions).

- **chess_players**: `id`, `open_id` (derived from the mock login code),
  `nickname`, `avatar_url`
- **chess_sessions**: `id`, `token` (unique), `player_id`, `expires_at`
- **chess_rooms**: `id`, `red_player_id`, `black_player_id`, `fen`, `turn`,
  `status` (playing / check / checkmate / draw / stalemate)
- **chess_moves**: `id`, `room_id`, `seq`, `color`, `from_row`, `from_col`,
  `to_row`, `to_col`, `piece`, `captured`, `iccs` — move history for a room,
  since the room row only holds the current FEN
- **chess_queue_entries**: `id`, `player_id`, `joined_at` — matchmaking
  waiting list

## Rules engine (`service/chess/rules.py`)

Reimplements what `xiangqi.js` provides today:

- 10x9 board representation with the seven Xiangqi piece types (king,
  advisor, elephant, horse, chariot, cannon, soldier)
- Per-piece legal-move generation, including palace boundaries for
  king/advisor and river-crossing rules for elephant/soldier
- The "flying general" rule: the two kings may never face each other on an
  open file with no piece between them
- Check detection
- Checkmate/stalemate detection: for the side to move, enumerate all legal
  moves; if none escape check, checkmate; if none exist without being in
  check, stalemate
- FEN-equivalent serialization/parsing to persist board state as a string on
  `chess_rooms.fen`, and `position <-> iccs` conversion helpers mirroring
  `positionToIccs`/`iccsToPosition` in chess-server's `rules.ts`

## API surface (mounted at `/chess`, same prefix-mount pattern as
`english`/`peach` in `routes/__init__.py`)

- `POST /chess/auth/wechat-login` — body `{code}` -> `{player, session}`
- `POST /chess/matchmaking/join` — bearer token -> `{status: queued}` or
  `{status: matched, room}`
- `GET /chess/matchmaking/status` — bearer token -> current queue/matched
  state (new; replaces the WebSocket push from chess-server)
- `POST /chess/matchmaking/leave` — bearer token
- `GET /chess/rooms/{room_id}` — poll current room/board state
- `POST /chess/rooms/{room_id}/move` — body `{from, to, client_move_id}` ->
  accepted/rejected + room

Bearer token extraction follows chess-server's `getBearerToken` pattern.
Responses use `app/response.py`'s `api_response`, same `{code, msg, data}`
shape as `english`/`peach`.

## Error handling

Follows the existing project convention: service functions return
`{code, msg}` / `{code, msg, data}` dicts, wrapped by `api_response`.
Unexpected exceptions go through `unexpected_error_response` (log,
rollback, generic 500), same as `service/english/words.py`.

## Testing

- `tests/chess/test_rules.py` — pure unit tests, no DB: move legality per
  piece type, the flying-general rule, check/checkmate/stalemate/draw
  detection, FEN round-trip. Mirrors chess-server's rules coverage.
- `tests/chess/test_auth.py`, `tests/chess/test_matchmaking.py` —
  service-layer tests against an in-memory SQLite engine (swapped in via a
  pytest fixture overriding `get_db`), since there is no test-MySQL instance
  in this project. Mirrors the intent of `auth.test.ts`/`matchmaking.test.ts`.
- Adds `pytest` to `requirements.txt` under a new `# Testing` section.

## Out of scope

- WebSocket/real-time push (explicitly traded away for multi-worker
  correctness; polling instead)
- Any change to chess-server itself (left as-is, untouched)
- Reusing chess-server's rules logic across languages (no FFI/subprocess
  bridge — full native Python reimplementation instead)
