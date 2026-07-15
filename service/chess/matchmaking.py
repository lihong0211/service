# service/chess/matchmaking.py
"""
Chess 匹配与对局服务：排队、建房、提交着法、轮询状态
"""
from datetime import datetime

from app.database import db
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
