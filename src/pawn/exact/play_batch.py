"""Batch tablebase-vs-Stockfish validation: for each n and ruleset, play many
games with the tablebase on each side and tally wins/draws/losses.

The tablebase plays a random *value-preserving* (optimal) move each turn, so the
100 games differ; Stockfish plays the other side (as a move evaluator only, never
moving a king). A perfect player can never do worse than the game value against
any opponent, so we assert every game's result is at least the game value from
the tablebase's side -- in particular, on a non-losing side it never loses.
"""
from __future__ import annotations

import random

import chess
import chess.engine

from .refboard import RefBoard, WHITE, BLACK
from .fastsolver import FastSolver
from .positions import pawn_game_fen
from .play_stockfish import open_stockfish, stockfish_move, terminal_result, _rb_to_chess


def sf_move_fast(engine, rb, limit):
    """One Stockfish call per move (fast); fall back to per-child ranking if
    Stockfish returns a king move or something outside our legal pawn moves."""
    board = _rb_to_chess(rb)
    if board is not None:
        try:
            mv = engine.play(board, limit).move
        except Exception:  # noqa: BLE001
            mv = None
        if mv is not None and board.piece_type_at(mv.from_square) == chess.PAWN:
            for m in rb.legal_moves():
                if m[0] == mv.from_square and m[1] == mv.to_square:
                    return m
    return stockfish_move(engine, rb, limit)  # robust fallback


def tb_move_random(solver, rb, rng):
    """A random value-preserving (optimal) move for the side to move."""
    target = solver.value(rb)
    opts = []
    for m in rb.legal_moves():
        if RefBoard.is_touchdown(m):
            cv = 1
        else:
            rb.push(m); cv = -solver.value(rb); rb.pop()
        if cv == target:
            opts.append(m)
    if not opts:
        opts = rb.legal_moves()
    return rng.choice(opts)


def play_game(solver, n, sl, our_side, engine, limit, rng, justify="left"):
    rb = RefBoard.from_fen(pawn_game_fen(n, justify))
    for _ in range(300):
        t = terminal_result(rb, sl)
        if t is not None:
            return t
        if rb.turn == our_side:
            mv = tb_move_random(solver, rb, rng)
        else:
            mv = sf_move_fast(engine, rb, limit)
        if RefBoard.is_touchdown(mv):
            return 1 if rb.turn == WHITE else -1
        rb.push(mv)
    return terminal_result(rb, sl) or 0


def main(nmax=6, games=100, depth=8):
    engine = open_stockfish()
    limit = chess.engine.Limit(depth=depth)
    print("n rule side theory  W  D  L   (tablebase perspective; %d games)" % games, flush=True)
    try:
        for n in range(1, nmax + 1):
            for sl, rule in [(True, "loss"), (False, "draw")]:
                solver = FastSolver(stalemate_is_loss=sl)
                vwhite = solver.value(RefBoard.from_fen(pawn_game_fen(n)))  # solve once, reuse
                for side, name in [(WHITE, "W"), (BLACK, "B")]:
                    gval = vwhite if side == WHITE else -vwhite
                    W = D = L = 0
                    for seed in range(games):
                        rng = random.Random((seed * 131 + n * 17 + (0 if sl else 5)) * 2 + side)
                        res = play_game(solver, n, sl, side, engine, limit, rng)
                        ours = res if side == WHITE else -res
                        if ours > 0: W += 1
                        elif ours == 0: D += 1
                        else: L += 1
                        assert ours >= gval, (n, rule, name, seed, ours, gval)
                    flag = "" if (gval < 0 or L == 0) else "  <-- LOSS ON NON-LOSING SIDE!"
                    print("%d %-4s %s   %+d   %3d %3d %3d%s" % (n, rule, name, gval, W, D, L, flag), flush=True)
    finally:
        engine.quit()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--nmax", type=int, default=6)
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--depth", type=int, default=8)
    args = ap.parse_args()
    main(args.nmax, args.games, args.depth)
