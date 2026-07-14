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
