"""Perfect-play engine for the pawn game (chess with pawns only, no kings).

Generate the exact tablebase for the $n$-versus-$n$ pawn game and then query it
like a chess engine: given any kingless position, get an optimal (value-preserving)
move, all optimal moves, or the exact value. Because a solved tablebase plays
perfectly, this is a drop-in "perfect player" for the kingless pawn game -- the
analogue of plugging in Stockfish, except every move is provably optimal.

Two backends, same API:

* ``backend="cpp"``    -- drives the compiled C++ solver's move server
  (``pawnsolver_par ... --serve``). Fast; the right choice for $n\\ge 6$ or many
  queries. Needs the binary built (see the project README, or ``binary=``/``PAWN_SRV``).
* ``backend="python"`` -- the pure-Python :class:`FastSolver`. No build step;
  best for $n\\le 6$, teaching, and cross-checking the C++ core.

Positions are FENs of the pawns-only board (no kings). The $n$-pawn start is
``pawn_game_fen(n)``. Values are from the point of view named in each method and
use ``+1`` (White/side-to-move wins), ``0`` (draw), ``-1`` (loss).

Example
-------
>>> from pawn.exact.engine import PawnEngine
>>> from pawn.exact.positions import pawn_game_fen
>>> with PawnEngine(8, rule="loss") as eng:      # solve 8-vs-8 under the loss rule
...     eng.value                                 # +1: White wins the 8-pawn game
1
...     start = pawn_game_fen(8)
...     eng.best_moves(start)                     # every optimal first move (UCI)
['b2b4', 'c2c4', 'f2f4', 'g2g4']
...     eng.best_move(start, seed=1)              # one optimal move, deterministic
'c2c4'
...     eng.evaluate("8/8/8/p7/P7/8/8/8 w - - 0 1")   # value from side to move
-1

CLI (a minimal engine loop over stdin, like a UCI server but kingless)::

    $ python -m pawn.exact.engine 8 loss
    value 1
    ready
    bestmove 8/8/8/p7/P7/8/8/8 w - - 0 1      # you type a FEN...
    a4a5                                       # ...it replies with an optimal move
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import List, Optional, Union

from .refboard import RefBoard, WHITE, BLACK
from .positions import pawn_game_fen

Pos = Union[str, RefBoard]

_DEFAULT_BINARY = os.path.join(os.path.dirname(__file__), "..", "..", "cpp", "pawnsolver_par")


def _fen(pos: Pos) -> str:
    """Accept a FEN string or a :class:`RefBoard`; return a FEN string."""
    return pos if isinstance(pos, str) else pos.fen()


class PawnEngine:
    """A solved-tablebase perfect player for the $n$-versus-$n$ pawn game.

    Parameters
    ----------
    n : int
        Pawns per side (1..8).
    rule : {"loss", "draw"}
        How "no legal move" scores: ``"loss"`` (the game's stated rule) or
        ``"draw"`` (chess stalemate).
    backend : {"cpp", "python"}
        Solver to use. ``"cpp"`` drives the compiled move server; ``"python"``
        uses the in-process :class:`FastSolver`.
    ep : bool
        Include en passant in the rules (default ``True``). ``False`` reproduces
        the no-en-passant experiments.
    threads, minsub, bits : int, optional
        C++ backend tuning (ignored by the Python backend). ``threads`` defaults
        to all cores; ``bits`` sizes the transposition table (``2**bits`` slots);
        ``minsub`` is the subtree-storage threshold. Sensible defaults are chosen
        per ``n`` if not given.
    binary : str, optional
        Path to the C++ solver (else ``$PAWN_SRV`` or the in-tree build).
    """

    def __init__(self, n: int, rule: str = "loss", backend: str = "cpp", *,
                 ep: bool = True, threads: Optional[int] = None,
                 minsub: int = 16, bits: Optional[int] = None,
                 binary: Optional[str] = None):
        if rule not in ("loss", "draw"):
            raise ValueError("rule must be 'loss' or 'draw'")
        if backend not in ("cpp", "python"):
            raise ValueError("backend must be 'cpp' or 'python'")
        self.n, self.rule, self.backend, self.ep = n, rule, backend, ep
        self._proc = None
        if backend == "python":
            from .fastsolver import FastSolver
            if not ep:
                raise NotImplementedError("the python backend always uses en passant; "
                                          "use backend='cpp' with ep=False")
            self._solver = FastSolver(stalemate_is_loss=(rule == "loss"))
            self._value = self._solver.value(RefBoard.from_fen(pawn_game_fen(n)))
        else:
            self._start_server(threads, minsub, bits, binary)

    # ---- lifecycle -------------------------------------------------------
    def _start_server(self, threads, minsub, bits, binary):
        binary = binary or os.environ.get("PAWN_SRV") or _DEFAULT_BINARY
        if not os.path.exists(binary):
            raise FileNotFoundError(
                f"C++ solver not found at {binary!r}. Build it first "
                f"(see README: `make` or the clang++ line), or pass binary=/PAWN_SRV, "
                f"or use backend='python'.")
        if threads is None:
            threads = os.cpu_count() or 1
        if bits is None:
            bits = {5: 25, 6: 28, 7: 31, 8: 33}.get(self.n, 22)
        extra = ["--colorsym", f"--threads={threads}", f"--minsub={minsub}", f"--bits={bits}"]
        if not self.ep:
            extra.append("--noep")
        self._proc = subprocess.Popen(
            [binary, str(self.n), self.rule, "--serve", *extra],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self._value = None
        for line in self._proc.stdout:                 # read the solve summary, then READY
            if line.startswith("n="):
                self._value = int(line.split("value=")[1].split()[0])
            if line.strip() == "READY":
                break
        if self._value is None:
            raise RuntimeError("solver did not report a value; check the binary/flags")

    def _cmd(self, line: str) -> str:
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()
        return self._proc.stdout.readline().strip()

    def close(self):
        """Shut the C++ server down (no-op for the Python backend)."""
        if self._proc is not None:
            try:
                self._proc.stdin.write("quit\n"); self._proc.stdin.flush()
            except Exception:  # noqa: BLE001
                pass
            self._proc.terminate()
            self._proc = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- queries ---------------------------------------------------------
    @property
    def value(self) -> int:
        """Game value of the $n$-versus-$n$ start, from **White's** point of view
        (``+1`` White wins, ``0`` draw, ``-1`` Black wins)."""
        return self._value

    def evaluate(self, pos: Pos) -> int:
        """Exact value of ``pos`` from the **side to move** (``+1``/``0``/``-1``)."""
        if self.backend == "python":
            return self._solver.value(pos if isinstance(pos, RefBoard)
                                      else RefBoard.from_fen(pos))
        return int(self._cmd("eval " + _fen(pos)))

    def best_moves(self, pos: Pos) -> List[str]:
        """Every optimal (value-preserving) move in ``pos``, in UCI (e.g. ``b2b4``,
        ``a5b6`` for a capture). Empty if the position is terminal."""
        if self.backend == "python":
            return self._py_best(pos, all_moves=True)
        out = self._cmd("opts " + _fen(pos))
        return [] if out in ("terminal", "none", "") else out.split()

    def best_move(self, pos: Pos, seed: Optional[int] = None) -> Optional[str]:
        """One optimal move in ``pos`` (UCI), or ``None`` if terminal. The C++
        backend picks uniformly at random among the optimal moves; pass ``seed``
        for a reproducible choice."""
        if self.backend == "python":
            ms = self._py_best(pos, all_moves=False, seed=seed)
            return ms[0] if ms else None
        if seed is not None:
            self._cmd("seed %d" % (seed & 0xFFFFFFFF))
        out = self._cmd(_fen(pos))
        return None if out in ("terminal", "none", "") else out

    # ---- python-backend helpers -----------------------------------------
    def _py_best(self, pos: Pos, all_moves: bool, seed: Optional[int] = None):
        b = pos if isinstance(pos, RefBoard) else RefBoard.from_fen(pos)
        if b.opp_pawns() == 0 or b.my_pawns() == 0:
            return []
        moves = b.legal_moves()
        if not moves:
            return []
        v = self._solver.value(b)
        opts = []
        for m in moves:
            if RefBoard.is_touchdown(m):
                cv = 1
            else:
                b.push(m); cv = -self._solver.value(b); b.pop()
            if cv == v:
                opts.append(m)
        uci = [_move_uci(m) for m in opts]
        if all_moves:
            return uci
        if not uci:
            return []
        import random
        return [random.Random(seed).choice(uci)]


def _move_uci(m) -> str:
    frm, to, _ = m
    return "abcdefgh"[frm & 7] + str((frm >> 3) + 1) + "abcdefgh"[to & 7] + str((to >> 3) + 1)


def _cli(argv):
    """A tiny stdin move server: `python -m pawn.exact.engine <n> <rule>`.
    Prints `value <v>` and `ready`, then for each FEN line prints an optimal move
    (or `eval <fen>` -> a value, `opts <fen>` -> all optimal moves, `quit`)."""
    n = int(argv[0]); rule = argv[1] if len(argv) > 1 else "loss"
    backend = argv[2] if len(argv) > 2 else "cpp"
    with PawnEngine(n, rule, backend=backend) as eng:
        print("value", eng.value, flush=True)
        print("ready", flush=True)
        for line in sys.stdin:
            line = line.strip()
            if line == "quit" or not line:
                if line == "quit":
                    break
                continue
            if line.startswith("eval "):
                print(eng.evaluate(line[5:]), flush=True)
            elif line.startswith("opts "):
                print(" ".join(eng.best_moves(line[5:])) or "terminal", flush=True)
            else:
                print(eng.best_move(line) or "terminal", flush=True)


if __name__ == "__main__":
    _cli(sys.argv[1:])
