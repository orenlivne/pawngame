# The Pawn Game, Solved

Exact solution of **the pawn game** — chess played with pawns only, no kings — for
$n = 1,\dots,8$ pawns per side, under both rulesets, with an open-source solver, an
independent reference oracle, a perfect-play **engine API**, and scripts that
reproduce every number in the paper.

> **Rules.** Each side starts with $n$ pawns on its home rank (files $a\dots$,
> left-justified for $n<8$). Pawns move, capture, double-step and take *en passant*
> exactly as in chess. A player wins by (a) reaching the last rank (*touchdown*),
> (b) capturing all enemy pawns, or (c) leaving the opponent with **no legal move**.
> Rule (c) is scored two ways, both solved here: **loss rule** (no move = loss — the
> game's stated rule) and **draw rule** (no move = draw — chess stalemate).

**Headline results** (value from White's point of view; `1/2` = draw):

| $n$        | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|------------|---|---|---|---|---|---|---|---|
| loss rule  | B | B | B | **W** | B | **W** | **W** | **W** |
| draw rule  | ½ | B | ½ | **W** | ½ | **W** | ½ | **W** |

The eight-pawn game is a first-player (White) win under **both** rules. **En passant
is essential**: removing it flips four of the sixteen values (every White win under
the draw rule, $n=4,6,8$, and the seven-pawn game under the loss rule).

The full write-up is in [`paper/pawngame.tex`](paper/pawngame.tex) (a SAGE
journal-styled version is in [`submission/`](submission/)); raw solver output for
every claim is in [`gcp/results/`](gcp/results/).

---

## Contents
- [Install](#install)
- [Build the C++ solver](#build-the-c-solver)
- [Quick start](#quick-start)
- [Engine API — a perfect player](#engine-api--a-perfect-player)
- [Reproduce the paper](#reproduce-the-paper)
- [Tests](#tests)
- [Repository layout](#repository-layout)
- [How the solver works](#how-the-solver-works)
- [Citation](#citation)

## Install

Python 3.10+ and (for the fast solver) a C++17 compiler.

```bash
# option A: conda/mamba
mamba env create -f environment.yml && mamba activate pawngame
# option B: pip
pip install python-chess pytest      # python-chess is only needed for the fuzz tests / Stockfish eval
```

The pure-Python engine and solver need **no build**. The C++ core is only needed
for $n\ge 6$ and for speed.

## Build the C++ solver

```bash
make                      # builds src/cpp/pawnsolver_par (auto-detects the platform)
```

`make` picks the right flags: on Apple Silicon `clang++ -O3 -std=c++17 -pthread`;
on x86-64 Linux it adds `-mcx16 -latomic` for lock-free 128-bit atomics. To build by
hand, see the `Makefile` or:

```bash
clang++ -O3 -std=c++17 -pthread -mcx16 -latomic -o src/cpp/pawnsolver_par src/cpp/pawnsolver_par.cpp
```

## Quick start

Solve a game from the command line and print the value, optimal openings, and the
principal variation:

```bash
./src/cpp/pawnsolver_par 8 loss --colorsym --threads=8 --minsub=16 --bits=33 --pv
# -> n=8 rule=loss ... value=1 (WHITE wins) ...
#    optimal_first_moves: b2b4 c2c4 f2f4 g2g4
#    pv: b2b4 a7a5 b4a5 ...
```

Flags: `loss|draw` (ruleset), `--colorsym` (color symmetry), `--threads=N`,
`--minsub=T` (subtree-storage threshold; larger = less memory, more recompute),
`--bits=K` (transposition table has `2**K` slots), `--noep` (disable en passant),
`--pv` (print the principal variation and every optimal first move).

## Engine API — a perfect player

Once solved, the tablebase plays **perfectly**: it is a drop-in engine for the
kingless pawn game — like plugging in Stockfish, except every move is provably
optimal. Use it from Python:

```python
from pawn.exact.engine import PawnEngine
from pawn.exact.positions import pawn_game_fen

# Solve 8-vs-8 under the loss rule (C++ backend; use backend="python" for n<=6, no build)
with PawnEngine(8, rule="loss") as eng:
    eng.value                       # +1  -> White wins the 8-pawn game
    start = pawn_game_fen(8)        # the kingless start FEN, White to move
    eng.best_moves(start)           # ['b2b4', 'c2c4', 'f2f4', 'g2g4']  (all optimal)
    eng.best_move(start, seed=1)    # 'c2c4'  (one optimal move; seed = reproducible)
    eng.evaluate(start)             # +1  (value from the side to move)
    eng.evaluate("8/8/8/p7/P7/8/8/8 w - - 0 1")   # -1  (White to move, stalemated)
```

`PawnEngine(n, rule, backend="cpp"|"python", ep=True, ...)` — positions are FENs of
the pawns-only board (or `RefBoard` objects); values are `+1/0/-1`. The C++ and
Python backends give identical answers (a tested invariant). See
[`src/pawn/exact/engine.py`](src/pawn/exact/engine.py) for the full docstring.

**Play against it / plug it into your own loop.** The engine speaks a tiny
line-oriented protocol over stdin/stdout — send a kingless FEN, get an optimal move
back (the same shape as a UCI `position`/`go`/`bestmove` loop, minus the kings):

```bash
python -m pawn.exact.engine 8 loss     # prints "value 1", then "ready", then:
# you send:   8/8/8/p7/P7/8/8/8 w - - 0 1      (a FEN)  -> engine replies: a4a5
# you send:   eval <fen>                                 -> +1 / 0 / -1
# you send:   opts <fen>                                 -> all optimal moves
# you send:   quit
```

The C++ binary exposes the same protocol directly (`pawnsolver_par n rule --serve`),
which is what the Stockfish play-test harness drives.

## Reproduce the paper

Everything is scripted and deterministic.

```bash
make                       # build the solver
./reproduce.sh values      # re-solve all n=1..8, both rules, +/- en passant -> the value tables
./reproduce.sh tests       # run the full test suite (oracle fuzz + cross-validation)
./reproduce.sh stockfish   # tablebase-vs-Stockfish play-test, winning side (needs stockfish on PATH)
./reproduce.sh all         # all of the above
```

Each paper artifact maps to a command (all outputs also archived in `gcp/results/`):

| Paper item | Regenerate with |
|---|---|
| Table: game values (both rules) | `./reproduce.sh values` |
| Table: with/without en passant  | `./reproduce.sh values` (runs `--noep` too) |
| Table: states / size / time     | the per-`n` `pawnsolver_par` lines printed by `values` |
| Table: tablebase vs Stockfish   | `./reproduce.sh stockfish` |
| Principal variations (appendix)  | `pawnsolver_par n rule --pv` → `paper/pv_to_san.py` |
| draw-rule $n=8$ (needs ~256 GB)  | `gcp/startup.sh` on a Google Cloud `n2-highmem-32` |

The largest solve (draw-rule $n=8$, ~58 GB table) needs a big-memory machine; the
cloud recipe used for the paper is in [`gcp/`](gcp/) (`startup.sh` builds, solves
every case, runs the play-test, uploads results, and self-deletes; `startup_sf.sh`
runs only the Stockfish play-test). Every value $n\le 7$ reproduces on a laptop.

## Tests

```bash
pytest -q                  # from the repo root
```

The suite establishes correctness independently of the paper's claims:
- **Move-generation fuzzing** against `python-chess` on random kingless positions
  and random play-outs (`test_refboard.py`).
- **Cross-validation**: the accelerated solver (symmetry, subtree caching, race
  evaluator) equals unpruned search, and the C++ core matches the Python oracle
  (`test_cpp_cross.py`, `test_engine.py`).

## Repository layout

```
paper/            LaTeX manuscript (pawngame.tex) + pv_to_san.py
submission/       SAGE (ICGA) journal-styled manuscript, cover letter, metadata
src/pawn/exact/   the solver package:
  refboard.py       kingless bitboard engine (fuzz-validated vs python-chess)
  refsolver.py      pure-minimax reference oracle (ground truth)
  fastsolver.py     accelerated solver (symmetry + subtree caching + race evaluator)
  passers.py        the proved passed-pawn race evaluator
  symmetry.py       the board symmetry group
  positions.py      left-justified start FENs
  engine.py         >>> the perfect-play engine API (this file) <<<
  play_stockfish.py, play_batch*.py   Stockfish play-test harnesses
src/cpp/          pawnsolver_par.cpp (parallel core, also the --serve move server)
gcp/              cloud run scripts (startup.sh, startup_sf.sh) + results/ (raw output)
results/          small precomputed tablebases (n<=4, Python pickle)
```

## How the solver works

The game is a finite DAG (every move advances a pawn, so play ends within 96 plies,
with no repetitions), hence solvable by retrograde/negamax search. Speed comes from
(1) a **proved passed-pawn race evaluator** that settles many nodes without
expanding them (exact under the loss rule; two-sided bounds under the draw rule),
(2) the board **symmetry group** (left–right mirror × color-swap-with-flip),
(3) a packed **transposition table** (16 bytes/position), and (4) a **lock-free
parallel search** over that shared table. Correctness never depends on the
shortcuts: each is cross-checked against unpruned search. Details in the paper.

## Citation

If you use this work, please cite the paper (see `paper/pawngame.tex`):

```bibtex
@article{livne_pawngame,
  title   = {Exact Solution of the Pawn Game for up to Eight Pawns per Side},
  author  = {Livne, Oren},
  journal = {ICGA Journal (submitted)},
  year    = {2026},
  note    = {https://github.com/orenlivne/pawngame}
}
```

## License

MIT — see [`LICENSE`](LICENSE).
