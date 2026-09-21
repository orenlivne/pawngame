"""Accelerated exact solver: minimax + proven race evaluator + LR symmetry.

Every value stored is exact (no alpha-beta bound entries), so the whole table can
be cross-checked against the pure oracle key-for-key.  The only shortcuts are:

  * definitional terminals (opp has no pawns / I have no pawns / no legal move /
    immediate touchdown), and
  * the *proven* passed-pawn race evaluator in :mod:`pawn.exact.passers`.

Positions are memoized under an LR-canonical key, halving the table.  Best moves
are not stored; PV / certificate extraction re-derives them from the value table
with one-ply lookahead (see :mod:`pawn.exact.certificate`).
"""
from __future__ import annotations

import sys
from typing import Dict

from .refboard import RefBoard
from .passers import race_value
from .symmetry import canonical

WIN, DRAW, LOSS = 1, 0, -1
sys.setrecursionlimit(1_000_000)


class FastSolver:
    def __init__(self, stalemate_is_loss: bool = True, use_race: bool = True,
                 use_symmetry: bool = True):
        self.stalemate_is_loss = stalemate_is_loss
        self.use_race = use_race
        self.use_symmetry = use_symmetry
        self.memo: Dict[tuple, int] = {}

    def _ckey(self, board: RefBoard):
        k = board.key()
        return canonical(k) if self.use_symmetry else k

    def value(self, board: RefBoard) -> int:
        ck = self._ckey(board)
        hit = self.memo.get(ck)
        if hit is not None:
            return hit

        if board.opp_pawns() == 0:
            self.memo[ck] = WIN
            return WIN
        if board.my_pawns() == 0:
            self.memo[ck] = LOSS
            return LOSS

        moves = board.legal_moves()
        if not moves:
            v = LOSS if self.stalemate_is_loss else DRAW
            self.memo[ck] = v
            return v

        for m in moves:
            if RefBoard.is_touchdown(m):
                self.memo[ck] = WIN
                return WIN

        # The race evaluator is only sound under the loss-rule: under the
        # draw-rule, getting stalemated is a *drawing* resource that can beat
        # losing the race (see passers.py), so we must search instead.
        if self.use_race and self.stalemate_is_loss:
            rv = race_value(board)
            if rv is not None:
                self.memo[ck] = rv
                return rv

        best = LOSS - 1
        for m in _ordered(board, moves):
            board.push(m)
            child = self.value(board)
            board.pop()
            cand = -child
            if cand > best:
                best = cand
                if best == WIN:
                    break
        self.memo[ck] = best
        return best


def _ordered(board: RefBoard, moves):
    opp = board.opp_pawns()
    white = board.turn == 0

    def score(m):
        frm, to, is_ep = m
        s = 0
        if is_ep or (opp & (1 << to)):
            s += 100
        r = to >> 3
        s += r if white else (7 - r)
        return -s

    return sorted(moves, key=score)


def solve(fen: str, stalemate_is_loss: bool = True, **kw):
    solver = FastSolver(stalemate_is_loss=stalemate_is_loss, **kw)
    return solver.value(RefBoard.from_fen(fen)), solver
