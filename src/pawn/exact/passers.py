"""Provably-correct passed-pawn *race* evaluation.

This lets the solver decide many positions without searching below them, but --
unlike a heuristic -- every value it returns is a theorem.  It is the only
"shortcut" the fast solver trusts, and it is cross-validated against the pure
minimax oracle on every shared position for n<=6.

Definitions (side to move = "me"; I move on odd plies 1,3,5..., my k-th move is
ply 2k-1; the opponent moves on even plies, k-th move at ply 2k):

  * An **unstoppable passer** is a pawn with no *enemy* pawn on its file or the
    two adjacent files ahead of it.  It can be neither blocked nor captured, so
    by pushing it every move its owner promotes in exactly ``steps`` of their own
    moves, no matter what the other side does.  (A friendly pawn ahead only means
    a *front* pawn on that file promotes even sooner, so the per-side minimum is
    unaffected.)
      a = min steps over MY  unstoppable passers   (INF if I have none)
      b = min steps over OPP unstoppable passers   (INF if none)
  * A **promotion lower bound** ignores all obstacles: the fewest moves a pawn
    could *possibly* need to reach the last rank (rank distance, minus one if it
    can still double from its start rank).  It lower-bounds that side's earliest
    possible win *by any means* in the situations below.
      cw = min lower bound over ALL my  pawns
      cb = min lower bound over ALL opp pawns

Theorems (proof sketch in each branch):

  (WIN)  if a <= cb:  return WIN
     I promote at ply 2a-1 by pushing my unstoppable passer.  The opponent's
     passer is uncapturable, so I can never capture all their pawns and they are
     never stalemated -- their ONLY way to win is to promote, needing >= cb of
     their moves, i.e. not before ply 2*cb >= 2a > 2a-1.  So I win first. ∎

  (LOSS) if b < cw:   return LOSS
     Symmetric: the opponent promotes at ply 2b (guaranteed).  Their passer is
     uncapturable and they are never stalemated while pushing it, so my only way
     to win is to promote, needing >= cw of my moves, i.e. not before ply
     2*cw-1.  cw > b  =>  2*cw-1 >= 2b+1 > 2b, so the opponent wins first. ∎

  otherwise: return None  (must search).

The two branches never conflict (a <= cb <= b and b < cw <= a is contradictory).

RULESET NOTE: this evaluator is sound ONLY under the **loss-rule** (no legal
move = loss).  The proofs above quietly use "getting stalemated is at worst a
loss for the stalemated side": under the loss-rule a stalemate is a loss, so
being stalemated before promoting only turns a race-loss into ... a loss (branch
LOSS), and the opponent being stalemated hands me the win (branch WIN).  Under
the **draw-rule** a stalemate is a *draw*, a genuine drawing resource that can
beat losing the race -- e.g. White's only pawn gets stalemated (draw) before
Black's unstoppable passer promotes.  So the caller must not use this under the
draw-rule; there we fall back to full search.
"""
from __future__ import annotations

from .refboard import WHITE, BLACK, bits

INF = 99

# _obstacle[color][sq] = squares ahead of `sq` in its file and the two adjacent
# files (an ENEMY pawn on any of them stops the pawn).
_obstacle = [[0] * 64 for _ in range(2)]
for _color in (WHITE, BLACK):
    _step = 8 if _color == WHITE else -8
    for _sq in range(64):
        _f = _sq & 7
        _mask = 0
        for _adj in (0, -1, 1):
            _nf = _f + _adj
            if 0 <= _nf <= 7:
                _s = _sq + _step + _adj
                while 0 <= _s < 64:
                    _mask |= 1 << _s
                    _s += _step
        _obstacle[_color][_sq] = _mask


def _steps_lb(sq: int, color: int) -> int:
    """Promotion lower bound: fewest moves this pawn could need (double allowed)."""
    rank = sq >> 3
    if color == WHITE:
        dist = 7 - rank
        if rank == 1:  # can double from the start rank
            dist -= 1
    else:
        dist = rank
        if rank == 6:
            dist -= 1
    return dist


def _min_promo_lb(pawns: int, color: int) -> int:
    best = INF
    for sq in bits(pawns):
        s = _steps_lb(sq, color)
        if s < best:
            best = s
    return best


def _min_unstoppable_steps(pawns: int, enemy: int, color: int, occ: int) -> int:
    """Min guaranteed moves-to-promote over this side's unstoppable passers."""
    best = INF
    for sq in bits(pawns):
        if _obstacle[color][sq] & enemy:
            continue  # an enemy pawn blocks or can capture it -> not unstoppable
        rank = sq >> 3
        if color == WHITE:
            dist = 7 - rank
            # Double only if genuinely on the start rank with both squares empty.
            if rank == 1 and not (occ & (1 << (sq + 8))) and not (occ & (1 << (sq + 16))):
                dist -= 1
        else:
            dist = rank
            if rank == 6 and not (occ & (1 << (sq - 8))) and not (occ & (1 << (sq - 16))):
                dist -= 1
        if dist < best:
            best = dist
    return best


def race_value(board):
    """Return WIN(+1)/LOSS(-1) if the passed-pawn race decides it, else None."""
    me = board.my_pawns()
    opp = board.opp_pawns()
    occ = board.wp | board.bp
    my_color = board.turn
    opp_color = BLACK if my_color == WHITE else WHITE

    a = _min_unstoppable_steps(me, opp, my_color, occ)
    cb = _min_promo_lb(opp, opp_color)
    if a <= cb:
        return 1

    b = _min_unstoppable_steps(opp, me, opp_color, occ)
    cw = _min_promo_lb(me, my_color)
    if b < cw:
        return -1

    return None
