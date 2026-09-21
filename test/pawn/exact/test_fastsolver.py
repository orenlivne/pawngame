"""Cross-validate the accelerated solver against the pure minimax oracle.

The oracle (ReferenceSolver) searches the full tree with only definitional
terminals.  The fast solver adds the proven race evaluator and LR symmetry.  If
those are correct, the two must agree on the root value AND on every position
they both evaluate.
"""
import random

import pytest

from pawn.exact.refboard import RefBoard, WHITE, BLACK
from pawn.exact.refsolver import ReferenceSolver
from pawn.exact.fastsolver import FastSolver
from pawn.exact.positions import pawn_game_fen
from pawn.exact.symmetry import fliplr_mask, fliplr_key, canonical


# ------------------------------------------------------------------ symmetry
def test_fliplr_involution():
    rng = random.Random(0)
    for _ in range(1000):
        m = rng.getrandbits(64)
        assert fliplr_mask(fliplr_mask(m)) == m


def test_fliplr_files_mirror():
    # a single pawn on a2 (sq 8) mirrors to h2 (sq 15)
    assert fliplr_mask(1 << 8) == (1 << 15)
    assert fliplr_mask(1 << 12) == (1 << 11)  # e-file <-> d-file (sq 12 -> 11)


def _random_position(rng, max_pawns=4):
    squares = list(range(8, 56))
    rng.shuffle(squares)
    nw = rng.randint(1, max_pawns)
    nb = rng.randint(1, max_pawns)
    wp = bp = 0
    i = 0
    for _ in range(nw):
        wp |= 1 << squares[i]; i += 1
    for _ in range(nb):
        bp |= 1 << squares[i]; i += 1
    return RefBoard(wp, bp, rng.choice([WHITE, BLACK]), None)


@pytest.mark.parametrize("stalemate_is_loss", [True, False])
def test_oracle_value_is_lr_invariant(stalemate_is_loss):
    """value(pos) == value(mirror(pos)) for random positions (pure oracle)."""
    rng = random.Random(7)
    solver = ReferenceSolver(stalemate_is_loss=stalemate_is_loss)
    for _ in range(300):
        b = _random_position(rng)
        v = solver.value(b)
        fk = fliplr_key(b.key())
        mb = RefBoard(fk[0], fk[1], fk[2], fk[3])
        assert solver.value(mb) == v, b.fen()


# ---------------------------------------------------------- cross-validation
def _cross_check(n, stalemate_is_loss):
    fen = pawn_game_fen(n)
    oracle = ReferenceSolver(stalemate_is_loss=stalemate_is_loss)
    v_oracle = oracle.value(RefBoard.from_fen(fen))

    fast = FastSolver(stalemate_is_loss=stalemate_is_loss)
    v_fast = fast.value(RefBoard.from_fen(fen))
    assert v_fast == v_oracle, (n, stalemate_is_loss, v_fast, v_oracle)

    # Every position the fast solver evaluated must match the oracle's value for
    # the same (canonical) position.
    ocanon = {}
    for k, (val, _mv) in oracle.memo.items():
        ck = canonical(k)
        if ck in ocanon:
            assert ocanon[ck] == val, ("oracle not LR-consistent", ck)
        ocanon[ck] = val
    shared = 0
    for ck, val in fast.memo.items():
        if ck in ocanon:
            assert ocanon[ck] == val, ("fast disagrees with oracle", ck, val, ocanon[ck])
            shared += 1
    assert shared > 0
    return v_fast


@pytest.mark.parametrize("n", [1, 2, 3, 4])
@pytest.mark.parametrize("stalemate_is_loss", [True, False])
def test_fast_matches_oracle(n, stalemate_is_loss):
    _cross_check(n, stalemate_is_loss)


@pytest.mark.parametrize("n", [1, 2, 3, 4])
@pytest.mark.parametrize("stalemate_is_loss", [True, False])
def test_race_shortcut_matches_pure_fast(n, stalemate_is_loss):
    """FastSolver with and without the race evaluator must agree at the root."""
    fen = pawn_game_fen(n)
    with_race = FastSolver(stalemate_is_loss=stalemate_is_loss, use_race=True)
    no_race = FastSolver(stalemate_is_loss=stalemate_is_loss, use_race=False)
    assert with_race.value(RefBoard.from_fen(fen)) == no_race.value(RefBoard.from_fen(fen))


def test_known_results_loss_rule():
    """Locks in the verified left-justified loss-rule headline for n=1..4."""
    expected = {1: -1, 2: -1, 3: -1, 4: 1}
    for n, exp in expected.items():
        fast = FastSolver(stalemate_is_loss=True)
        assert fast.value(RefBoard.from_fen(pawn_game_fen(n))) == exp, n


def test_known_results_draw_rule():
    expected = {1: 0, 2: -1, 3: 0, 4: 1}
    for n, exp in expected.items():
        fast = FastSolver(stalemate_is_loss=False)
        assert fast.value(RefBoard.from_fen(pawn_game_fen(n))) == exp, n
