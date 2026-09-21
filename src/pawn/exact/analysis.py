"""Extract perfect-play lines and best moves from a solved value table.

Best moves are re-derived from the value function with one-ply lookahead (no
move needs to be stored in the table).  At each position we pick a *value-
preserving* move -- for the winner that is a winning move, for the loser/drawer
any move that holds the value -- preferring touchdowns, then captures, then the
most advanced push, so the line reads naturally.  The resulting line is a valid
perfect game (the game is a finite DAG, so it always terminates).
"""
from __future__ import annotations

from typing import List, Optional

from .refboard import RefBoard, WHITE, square_name

WIN, DRAW, LOSS = 1, 0, -1


def move_uci(move) -> str:
    return square_name(move[0]) + square_name(move[1])


def _ordered(board: RefBoard, moves):
    opp = board.opp_pawns()
    white = board.turn == WHITE

    def score(m):
        frm, to, is_ep = m
        s = 0
        if RefBoard.is_touchdown(m):
            s += 1000
        if is_ep or (opp & (1 << to)):
            s += 100
        r = to >> 3
        s += r if white else (7 - r)
        return -s

    return sorted(moves, key=score)


def best_move(solver, board: RefBoard) -> Optional[tuple]:
    """A value-preserving optimal move (or None if terminal)."""
    moves = board.legal_moves()
    if not moves:
        return None
    v = solver.value(board)
    for m in _ordered(board, moves):
        if RefBoard.is_touchdown(m):
            if v == WIN:
                return m
            continue
        board.push(m)
        cv = -solver.value(board)
        board.pop()
        if cv == v:
            return m
    return _ordered(board, moves)[0]


def principal_variation(solver, board: RefBoard, max_plies=96) -> List[tuple]:
    b = RefBoard(board.wp, board.bp, board.turn, board.ep_sq)
    line = []
    for _ in range(max_plies):
        if b.opp_pawns() == 0 or b.my_pawns() == 0 or not b.has_legal_moves():
            break
        m = best_move(solver, b)
        if m is None:
            break
        line.append(m)
        b.push(m)
        if RefBoard.is_touchdown(m):
            break
    return line


def pv_string(solver, board: RefBoard) -> str:
    pv = principal_variation(solver, board)
    out = []
    b = RefBoard(board.wp, board.bp, board.turn, board.ep_sq)
    for i, m in enumerate(pv):
        if b.turn == WHITE:
            out.append("%d.%s" % (i // 2 + 1, move_uci(m)))
        else:
            out.append(move_uci(m))
        b.push(m)
    return " ".join(out)
