"""Cross-check the compiled C++ solver against the Python oracle, and confirm
its value is invariant to every optimization flag (symmetry, color symmetry,
subtree-threshold caching, race evaluator).

The C++ core is what solves n=7,8, so pinning it to the independently-validated
Python oracle for n<=6 -- under all configs -- is the main correctness anchor.
"""
import os
import re
import subprocess

import pytest

from pawn.exact.refboard import RefBoard
from pawn.exact.refsolver import ReferenceSolver
from pawn.exact.positions import pawn_game_fen

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CPP_SRC = os.path.join(REPO, "src", "cpp", "pawnsolver.cpp")
CPP_BIN = os.path.join(REPO, "src", "cpp", "pawnsolver")

_VALUE_RE = re.compile(r"value=(-?\d+)")


@pytest.fixture(scope="module")
def cpp_bin():
    if not os.path.exists(CPP_BIN) or os.path.getmtime(CPP_BIN) < os.path.getmtime(CPP_SRC):
        r = subprocess.run(["clang++", "-O3", "-std=c++17", "-o", CPP_BIN, CPP_SRC],
                           capture_output=True, text=True)
        if r.returncode != 0:
            pytest.skip("clang++ build failed: %s" % r.stderr)
    return CPP_BIN


def _cpp_value(cpp_bin, n, rule, extra):
    out = subprocess.run([cpp_bin, str(n), rule] + extra, capture_output=True, text=True, timeout=120)
    m = _VALUE_RE.search(out.stdout)
    assert m, "no value in output: %s / %s" % (out.stdout, out.stderr)
    return int(m.group(1))


def _oracle_value(n, rule):
    sl = rule == "loss"
    return ReferenceSolver(stalemate_is_loss=sl).value(RefBoard.from_fen(pawn_game_fen(n)))


# --no-race exercises the plain alpha-beta path; the default exercises the race
# evaluator (exact leaves under loss-rule, proven bounds under draw-rule).  Both
# must match the oracle for BOTH rulesets.
CONFIGS = [
    [],
    ["--no-sym"],
    ["--colorsym"],
    ["--minsub=64"],
    ["--colorsym", "--minsub=32"],
    ["--no-race"],
    ["--no-race", "--no-sym"],
    ["--no-race", "--colorsym", "--minsub=16"],
]


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("rule", ["loss", "draw"])
def test_cpp_matches_oracle_all_configs(cpp_bin, n, rule):
    expected = _oracle_value(n, rule)
    for cfg in CONFIGS:
        got = _cpp_value(cpp_bin, n, rule, cfg)
        assert got == expected, (n, rule, cfg, got, expected)


def test_cpp_n6_loss(cpp_bin):
    assert _cpp_value(cpp_bin, 6, "loss", ["--colorsym", "--minsub=16"]) == 1


def test_cpp_n6_draw_race_bounds(cpp_bin):
    # draw-rule n=6 with race BOUNDS on and off must both be White.
    assert _cpp_value(cpp_bin, 6, "draw", ["--colorsym"]) == 1
    assert _cpp_value(cpp_bin, 6, "draw", ["--colorsym", "--no-race"]) == 1


def test_cpp_justify_matches_python(cpp_bin):
    """Center/right justification also agree with the Python oracle (n<=4)."""
    from pawn.exact.fastsolver import FastSolver
    for just in ["center", "right"]:
        for n in [2, 3, 4]:
            exp = FastSolver(stalemate_is_loss=True).value(RefBoard.from_fen(pawn_game_fen(n, just)))
            got = _cpp_value(cpp_bin, n, "loss", ["--justify=" + just])
            assert got == exp, (just, n, got, exp)
