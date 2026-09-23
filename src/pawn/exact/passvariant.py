"""Independent reference solver for the *pass* rule variant of the pawn game.

In the pass variant a player may, on their turn, either make a normal pawn move or
**pass** -- but only if the opponent did not pass on the immediately preceding ply
(no two consecutive passes). That keeps the game finite and acyclic: passes cannot
chain, and every real move still advances the pawn monovariant of Proposition 1, so
no (position, side-to-move, en-passant, pass-right) state can repeat.

This module reuses the fuzz-validated :class:`RefBoard` pawn move generator and adds
only the pass bookkeeping, so it is an implementation independent of the C++ core --
its purpose is to cross-check the C++ pass solver on small n. It uses no symmetry or
pruning (plain memoized negamax), so it is slow but maximally trustworthy.

``solve_pass(n, rule)`` returns the value of the left-justified n-vs-n start from
White's point of view: +1 White win, 0 draw, -1 Black win.
"""
from __future__ import annotations

from .refboard import RefBoard, WHITE, BLACK
from .positions import pawn_game_fen


def solve_pass(n: int, rule: str = "loss") -> int:
    if rule not in ("loss", "draw"):
        raise ValueError("rule must be 'loss' or 'draw'")
    stalemate_is_loss = (rule == "loss")
    memo: dict = {}

    def val(b: RefBoard, canpass: bool) -> int:
        """Value from the side to move, given whether it may pass."""
        k = (b.wp, b.bp, b.turn, b.ep_sq, canpass)
        hit = memo.get(k)
        if hit is not None:
            return hit
        if b.opp_pawns() == 0:      # opponent has no pawns: side to move has won
            return 1
        if b.my_pawns() == 0:       # side to move has no pawns: it has lost
            return -1
        pawn_moves = b.legal_moves()
        for m in pawn_moves:
            if RefBoard.is_touchdown(m):
                memo[k] = 1
                return 1
        if not pawn_moves and not canpass:   # no legal move at all
            v = -1 if stalemate_is_loss else 0
            memo[k] = v
            return v

        best = -2
        for m in pawn_moves:
            b.push(m)
            cv = -val(b, True)      # a real move was made: opponent may now pass
            b.pop()
            if cv > best:
                best = cv
            if best == 1:
                break
        if best < 1 and canpass:    # try passing: opponent may then NOT pass
            saved = (b.turn, b.ep_sq)
            b.turn ^= 1
            b.ep_sq = None
            cv = -val(b, False)
            b.turn, b.ep_sq = saved
            if cv > best:
                best = cv
        memo[k] = best
        return best

    start = RefBoard.from_fen(pawn_game_fen(n))
    return val(start, True)


if __name__ == "__main__":
    import sys
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    for nn in range(lo, hi + 1):
        for rr in ("loss", "draw"):
            print("n=%d pass rule=%s value=%d" % (nn, rr, solve_pass(nn, rr)), flush=True)
