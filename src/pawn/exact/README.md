# Exact Pawn-Game Solver

A **foolproof** solver for the pawn game (pawns only, no kings — rules:
[adanhammod/pawn-game](https://github.com/adanhammod/pawn-game)). It determines,
with perfect play, whether the n-vs-n game (left-justified for n < 8) is a **win
for White, a win for Black, or a draw**, for n = 1..8, under **both** rulesets.

## The two rulesets

The three winning conditions are: reach the last rank ("touchdown"), capture all
opposing pawns, or leave the opponent with **no legal move**. That third one is
the crux:

* **loss-rule** (authoritative — matches the linked rules): no legal move = a
  **loss** for the side to move.
* **draw-rule** (chess stalemate): no legal move = a **draw**. (This is what an
  earlier version of this repo assumed.)

**Key fact.** Every legal move advances a pawn, and each of the ≤16 pawns advances
at most 6 times, so **every game ends within ≤96 plies** — the position graph is a
finite DAG with no repetitions. Under the loss-rule there are therefore **no draws
at all**: every start is a forced win for one side.

## Architecture

* `refboard.py` — an independent, clarity-first 8×8 bitboard pawn engine, used as
  the correctness oracle. Its move generation is fuzz-validated square-for-square
  against `python-chess` on kingless boards (random playouts, en passant, double
  pushes, touchdowns).
* `refsolver.py` — pure negamax + memoization with only *definitional* terminals.
  The ground-truth oracle.
* `passers.py` — a **proven** passed-pawn race evaluator (each returned value is a
  theorem; proof in the docstring). Sound only under the loss-rule (under the
  draw-rule, stalemate is a drawing resource that breaks the proof).
* `symmetry.py` — left-right file mirror; the C++ core adds color-swap∘vertical-
  flip. Together these are the full geometric symmetry group of the game.
* `fastsolver.py` — accelerated Python solver (race evaluator + symmetry),
  cross-validated against the oracle on every shared position.
* `analysis.py` — perfect-play line / opening-book extraction from a value table.
* `play_stockfish.py` — plays the tablebase against Stockfish (used only as a
  move *evaluator*; it never moves a king). A perfect side can never do worse than
  the game value against any opponent.
* `../../cpp/pawnsolver.cpp` — the C++ core that reaches n = 7, 8. Mirrors the
  Python semantics exactly (identical state counts through n = 6) with a compact
  open-addressing transposition table (16-byte packed keys), all symmetries, the
  race evaluator, leaf-skipping, and subtree-threshold caching for memory.

## Verification (why it is foolproof)

1. **Move generation** fuzz-tested against python-chess.
2. **Race evaluator** proven, and cross-validated against pure search on every
   shared position for n ≤ 6 (this caught a real bug: the shortcut is unsound
   under the draw-rule).
3. **Symmetries** proven value-invariant and cross-validated.
4. **C++ ↔ Python**: identical values (and state counts) for n ≤ 6, and value
   invariance across every optimization flag (`--colorsym`, `--minsub`,
   `--no-race`, `--no-sym`).
5. **Anchor**: the draw-rule + centered results reproduce the project's earlier
   hand-verified results (1→draw, 2→Black, 3→draw).
6. **Stockfish never-loses** play-test.

## Running

Python (n ≤ 6):

```bash
PYTHONPATH=src python -c "from pawn.exact.fastsolver import solve; \
  from pawn.exact.positions import pawn_game_fen; \
  print(solve(pawn_game_fen(5), stalemate_is_loss=True))"
```

C++ core (n up to 8):

```bash
clang++ -O3 -std=c++17 -o src/cpp/pawnsolver src/cpp/pawnsolver.cpp
# loss-rule n=8, memory-safe config (~17 GB): color symmetry + subtree threshold
src/cpp/pawnsolver 8 loss --colorsym --minsub=64 --bits=30
```

Tests:

```bash
python -m pytest test/pawn/exact/ -q
```

Stockfish play-test:

```bash
PYTHONPATH=src python -m pawn.exact.play_stockfish --n 5 --rule loss --depth 16
```

## Memory / performance notes

The solve is memory-bound, not compute-bound. Levers (all correctness-safe — they
change the cache, never a value): leaf-skip (~1.4×), color symmetry (~1.3×), and
`--minsub=T` (cache only nodes whose subtree had ≥ T new nodes; ~9× at T=64 for a
~1.7× time cost). `--minsub` makes n = 8 (loss) fit in ~17 GB. See `RESULTS.md`.
