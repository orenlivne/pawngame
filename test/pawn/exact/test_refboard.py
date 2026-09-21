"""Validate RefBoard's move generation and make/undo against python-chess.

python-chess is used purely as an independent oracle. We run on *kingless*
boards (the pawn game has no kings) and compare pseudo-legal pawn moves, which
for a pawns-only position equal the true legal moves (no pins or checks are
possible without sliders). Promotions are collapsed to their (from, to) square
pair since the pawn game has no promotion choice -- reaching the last rank just
wins.
"""
import random

import chess
import pytest

from pawn.exact.refboard import RefBoard, WHITE, BLACK, bits


def _pychess_pawn_pairs(fen):
    """(from, to) pairs of pseudo-legal pawn moves per python-chess, kingless."""
    board = chess.Board(fen)
    pairs = set()
    for m in board.generate_pseudo_legal_moves():
        if board.piece_type_at(m.from_square) == chess.PAWN:
            pairs.add((m.from_square, m.to_square))
    return pairs


def _ref_pawn_pairs(board):
    return {(m[0], m[1]) for m in board.legal_moves()}


def _random_position(rng, max_pawns=6):
    """A random kingless pawn position (pawns on ranks 2..7, i.e. squares 8..55)."""
    squares = list(range(8, 56))
    rng.shuffle(squares)
    nw = rng.randint(0, max_pawns)
    nb = rng.randint(0, max_pawns)
    wp = 0
    bp = 0
    idx = 0
    for _ in range(nw):
        wp |= 1 << squares[idx]
        idx += 1
    for _ in range(nb):
        bp |= 1 << squares[idx]
        idx += 1
    turn = rng.choice([WHITE, BLACK])
    return RefBoard(wp, bp, turn, None)


def _assert_matches(board):
    assert _ref_pawn_pairs(board) == _pychess_pawn_pairs(board.fen()), board.fen()


def test_start_positions_match_pychess():
    from pawn.exact.positions import pawn_game_fen
    for n in range(1, 9):
        b = RefBoard.from_fen(pawn_game_fen(n))
        _assert_matches(b)


def test_push_pop_roundtrip():
    rng = random.Random(1234)
    for _ in range(2000):
        b = _random_position(rng)
        before = b.key()
        for mv in b.legal_moves():
            b.push(mv)
            b.pop()
            assert b.key() == before, (before, mv, b.key())


@pytest.mark.parametrize("seed", list(range(40)))
def test_random_playout_matches_pychess(seed):
    """Play a random game; at every ply the legal-move set must equal python-chess."""
    rng = random.Random(seed)
    b = _random_position(rng)
    for _ply in range(200):
        # Compare move sets against the oracle.
        _assert_matches(b)
        moves = b.legal_moves()
        if not moves:
            break  # stalemate (terminal)
        # If a touchdown is available the game is over; verify the push works, stop.
        touchdowns = [m for m in moves if RefBoard.is_touchdown(m)]
        if touchdowns:
            b.push(touchdowns[0])
            break
        b.push(rng.choice(moves))
        # A side with no pawns is terminal.
        if b.wp == 0 or b.bp == 0:
            _assert_matches(b)
            break


def test_en_passant_white_captures():
    # Black just played c7-c5; white pawn d5 can take e.p. on c6.
    b = RefBoard.from_fen("8/8/8/2pP4/8/8/8/8 w - c6 0 1")
    pairs = _ref_pawn_pairs(b)
    assert (35, 42) in pairs  # d5 x c6 e.p.
    _assert_matches(b)
    # Make the e.p. capture: black pawn on c5 (square 34) must vanish.
    ep = [m for m in b.legal_moves() if m[2]][0]
    b.push(ep)
    assert b.bp == 0
    assert b.wp == (1 << 42)


def test_en_passant_black_captures():
    b = RefBoard.from_fen("8/8/8/8/3pP3/8/8/8 b - e3 0 1")
    ep = [m for m in b.legal_moves() if m[2]]
    assert ep, b.fen()
    b.push(ep[0])
    assert b.wp == 0
    assert b.bp == (1 << 20)  # e3


def test_ep_canonicalized_when_unusable():
    # ep square given but no black pawn adjacent to capture -> canonicalized away.
    b = RefBoard.from_fen("8/8/8/3P4/8/8/8/8 w - c6 0 1")
    assert b.ep_sq is None


def test_double_push_only_from_start_rank():
    b = RefBoard.from_fen("8/8/8/8/8/P7/8/8 w - - 0 1")  # white pawn on a3
    pairs = _ref_pawn_pairs(b)
    assert (16, 24) in pairs   # a3-a4
    assert (16, 32) not in pairs  # no a3-a5
