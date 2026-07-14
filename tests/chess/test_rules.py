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
