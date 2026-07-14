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
