"""Pure reference solver for the pawn game -- the correctness oracle.

This is deliberately the *simplest thing that is obviously correct*: full
negamax minimax with a transposition table, using only **definitional**
terminal rules (no passed-pawn heuristics, no alpha-beta bounds):

  * side to move has captured all opposing pawns             -> win  (+1)
  * side to move has no pawns left                           -> loss (-1)
  * side to move has an immediate touchdown move             -> win  (+1)
  * side to move has no legal move                           -> loss (-1) if
        the ruleset is "no-move = loss" (adanhammod), else draw (0)
  * otherwise the value is  max over moves of  -value(child)

Because every move advances a pawn and each of the <=16 pawns advances at most
6 times, the game DAG has depth <= ~96 and no repetitions, so plain minimax with
memoization terminates and returns the exact game-theoretic value.

Values are from the side-to-move's perspective: +1 win, -1 loss, 0 draw.
"""
from __future__ import annotations

import sys
from typing import Dict, Optional, Tuple

from .refboard import RefBoard

WIN, DRAW, LOSS = 1, 0, -1

sys.setrecursionlimit(1_000_000)


class ReferenceSolver:
    """Exact minimax solver.  ``stalemate_is_loss`` selects the ruleset."""

    def __init__(self, stalemate_is_loss: bool = True):
        self.stalemate_is_loss = stalemate_is_loss
        # key -> (value, best_move or None)
        self.memo: Dict[tuple, Tuple[int, Optional[tuple]]] = {}

    def value(self, board: RefBoard) -> int:
        return self._value(board)[0]

    def _value(self, board: RefBoard) -> Tuple[int, Optional[tuple]]:
        key = board.key()
        hit = self.memo.get(key)
        if hit is not None:
            return hit

        # Definitional terminals (do not depend on search).
        if board.opp_pawns() == 0:
            # Side to move has captured every opposing pawn: an immediate win.
            self.memo[key] = (WIN, None)
            return WIN, None
        if board.my_pawns() == 0:
            self.memo[key] = (LOSS, None)
            return LOSS, None

        moves = board.legal_moves()
        if not moves:
            v = LOSS if self.stalemate_is_loss else DRAW
            self.memo[key] = (v, None)
            return v, None

        # Immediate touchdown wins -- no need to search below.
        for m in moves:
            if RefBoard.is_touchdown(m):
                self.memo[key] = (WIN, m)
                return WIN, m

        best = LOSS - 1  # sentinel below any real value
        best_move = None
        for m in _ordered(board, moves):
            board.push(m)
            child = self._value(board)[0]
            board.pop()
            cand = -child
            if cand > best:
                best = cand
                best_move = m
                if best == WIN:  # cannot exceed a win; exact cutoff
                    break

        self.memo[key] = (best, best_move)
        return best, best_move

    # ------------------------------------------------------------- utilities
    def principal_variation(self, board: RefBoard):
        """Replays the perfect line from ``board`` (must be solved already)."""
        moves = []
        b = RefBoard(board.wp, board.bp, board.turn, board.ep_sq)
        while True:
            hit = self.memo.get(b.key())
            if hit is None:
                break
            _, mv = hit
            if mv is None:
                break
            moves.append(mv)
            b.push(mv)
        return moves


def _ordered(board: RefBoard, moves):
    """Move ordering: try likely-winning moves first so the WIN cutoff fires.

    Order: captures (incl. en passant) and the most-advanced pushes first.  This
    changes *speed only*, never the returned value.
    """
    white = board.turn == board.turn  # readability; board.turn is the mover
    opp = board.opp_pawns()

    def score(m):
        frm, to, is_ep = m
        s = 0
        # a capture (removes an opposing pawn) -- strong
        if is_ep or (opp & (1 << to)):
            s += 100
        # advancement toward promotion (rank distance travelled so far)
        r = to >> 3
        s += r if board.turn == 0 else (7 - r)
        return -s  # sort descending

    return sorted(moves, key=score)


def solve(fen: str, stalemate_is_loss: bool = True):
    """Solve a single position; returns (value, solver)."""
    solver = ReferenceSolver(stalemate_is_loss=stalemate_is_loss)
    board = RefBoard.from_fen(fen)
    return solver.value(board), solver
