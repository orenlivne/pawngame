"""Tests for the *pass* rule variant (a player may pass, but not twice in a row).

Checks (a) the independent Python reference values, (b) that the C++ solver agrees
with the Python reference on small n for both rulesets, and (c) the pass mechanics
(no two consecutive passes; a pass is a genuine tempo move).
"""
import os
import subprocess

import pytest

from pawn.exact.passvariant import solve_pass
from pawn.exact.refboard import RefBoard, WHITE, BLACK
from pawn.exact.positions import pawn_game_fen

_BIN = os.environ.get("PAWN_SRV") or os.path.join(
    os.path.dirname(__file__), "..", "..", "cpp", "pawnsolver_par")
_HAVE_CPP = os.path.exists(_BIN)

# Verified pass-variant values (White's POV): loss rule -> White wins (tempo/zugzwang);
# draw rule -> draw (passive play neutralizes the breakthrough).
EXPECTED = {
    (1, "loss"): 1, (2, "loss"): 1, (3, "loss"): 1, (4, "loss"): 1,
    (1, "draw"): 0, (2, "draw"): 0, (3, "draw"): 0, (4, "draw"): 0,
}


@pytest.mark.parametrize("n,rule", list(EXPECTED))
def test_reference_values(n, rule):
    assert solve_pass(n, rule) == EXPECTED[(n, rule)]


def _cpp_value(n, rule):
    out = subprocess.run(
        [_BIN, str(n), rule, "--pass", "--colorsym", "--minsub=1"],
        capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("n="):
            return int(line.split("value=")[1].split()[0])
    raise AssertionError("no value from C++ solver:\n" + out)


@pytest.mark.skipif(not _HAVE_CPP, reason="C++ solver not built (run `make`)")
@pytest.mark.parametrize("n,rule", list(EXPECTED))
def test_cpp_matches_reference(n, rule):
    assert _cpp_value(n, rule) == solve_pass(n, rule)


def test_pass_is_a_tempo_move_that_wins_1v1_under_loss():
    # 1-vs-1, loss rule: the passing option lets the first player force zugzwang.
    # Without passing this is a Black win; with passing it is a White win.
    from pawn.exact.fastsolver import FastSolver
    no_pass = FastSolver(stalemate_is_loss=True).value(
        RefBoard.from_fen(pawn_game_fen(1)))
    assert no_pass == -1                     # Black wins the ordinary 1-pawn loss game
    assert solve_pass(1, "loss") == 1        # White wins once passing is allowed


def test_no_two_consecutive_passes_keeps_it_finite():
    # solve_pass must terminate (the game is finite even with passing); if two
    # consecutive passes were allowed it would loop forever. Reaching here = pass.
    assert solve_pass(2, "draw") == 0
    assert solve_pass(3, "loss") == 1
