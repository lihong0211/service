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
