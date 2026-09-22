"""Tests for the perfect-play engine API (pawn.exact.engine.PawnEngine).

Establishes that (a) the values match the paper for small n and (b) the C++ and
Python backends agree exactly -- values, optimal-move sets, and per-position
evaluations. The C++ tests are skipped automatically if the binary is not built.
"""
import os

import pytest

from pawn.exact.engine import PawnEngine, _DEFAULT_BINARY
from pawn.exact.positions import pawn_game_fen

_HAVE_CPP = os.path.exists(os.environ.get("PAWN_SRV") or _DEFAULT_BINARY)

# White-POV game value of the n-vs-n start (from the paper).
EXPECTED = {
    (1, "loss"): -1, (2, "loss"): -1, (3, "loss"): -1, (4, "loss"): 1,
    (1, "draw"): 0,  (2, "draw"): -1, (3, "draw"): 0,  (4, "draw"): 1,
}


@pytest.mark.parametrize("n,rule", list(EXPECTED))
def test_python_values(n, rule):
    with PawnEngine(n, rule, backend="python") as e:
        assert e.value == EXPECTED[(n, rule)]


@pytest.mark.skipif(not _HAVE_CPP, reason="C++ solver not built (run `make`)")
@pytest.mark.parametrize("n,rule", list(EXPECTED))
def test_cpp_matches_python(n, rule):
    start = pawn_game_fen(n)
    with PawnEngine(n, rule, backend="cpp") as c, \
         PawnEngine(n, rule, backend="python") as p:
        assert c.value == p.value == EXPECTED[(n, rule)]
        assert set(c.best_moves(start)) == set(p.best_moves(start))
        assert c.evaluate(start) == p.evaluate(start)
        # a returned optimal move must be legal (present in the full move set)
        mv = c.best_move(start, seed=1)
        assert mv is None or mv in set(c.best_moves(start))


@pytest.mark.skipif(not _HAVE_CPP, reason="C++ solver not built (run `make`)")
def test_terminal_and_stalemate():
    # 1-vs-1 blocked (a4/a5): White to move is stalemated -> loss under the loss rule.
    with PawnEngine(1, "loss", backend="cpp") as e:
        assert e.best_move("8/8/8/p7/P7/8/8/8 w - - 0 1") is None   # no legal move
        assert e.evaluate("8/8/8/p7/P7/8/8/8 w - - 0 1") == -1
    # Same position is a draw under the draw rule.
    with PawnEngine(1, "draw", backend="cpp") as e:
        assert e.evaluate("8/8/8/p7/P7/8/8/8 w - - 0 1") == 0
