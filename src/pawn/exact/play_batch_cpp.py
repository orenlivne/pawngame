"""Tablebase-vs-Stockfish for larger n, using the C++ solver as a move server.

The C++ binary solves the game once (filling its transposition table), then
answers move queries on stdin: send a kingless FEN, receive a random optimal move
in UCI (or ``terminal``/``none``). This drives the same game loop as
:mod:`pawn.exact.play_batch`, but the perfect moves come from the C++ table, so it
scales to n=6,7,8 where the Python table would not fit in memory.
"""
from __future__ import annotations

import argparse
import subprocess

import chess
import chess.engine

from .refboard import RefBoard, WHITE, BLACK
from .positions import pawn_game_fen
from .play_stockfish import open_stockfish, terminal_result
from .play_batch import sf_move_fast

import os
CPP = os.environ.get("PAWN_SRV", "/Users/oren/code/chess/pawngame/src/cpp/pawnsolver_srv")


class Server:
    def __init__(self, n, rule, extra):
        self.p = subprocess.Popen([CPP, str(n), rule, "--serve"] + extra,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.value = None
        for line in self.p.stdout:
            if line.startswith("n="):
                self.value = int(line.split("value=")[1].split()[0])  # White's perspective
            if line.strip() == "READY":
                break

    def seed(self, s):
        self.p.stdin.write("seed %d\n" % s); self.p.stdin.flush()
        self.p.stdout.readline()

    def move(self, rb):
        self.p.stdin.write(rb.fen() + "\n"); self.p.stdin.flush()
        return self.p.stdout.readline().strip()

    def close(self):
        try:
            self.p.stdin.write("quit\n"); self.p.stdin.flush()
        except Exception:  # noqa: BLE001
            pass
        self.p.terminate()


def play_game(server, n, sl, our_side, engine, limit, gseed):
    server.seed(gseed)
    rb = RefBoard.from_fen(pawn_game_fen(n))
    for _ in range(400):
        t = terminal_result(rb, sl)
        if t is not None:
            return t
        if rb.turn == our_side:
            uci = server.move(rb)
            if uci in ("terminal", "none"):
                return terminal_result(rb, sl) or 0
            frm = "abcdefgh".index(uci[0]) + 8 * (int(uci[1]) - 1)
            to = "abcdefgh".index(uci[2]) + 8 * (int(uci[3]) - 1)
            mv = next(m for m in rb.legal_moves() if m[0] == frm and m[1] == to)
        else:
            mv = sf_move_fast(engine, rb, limit)
        if RefBoard.is_touchdown(mv):
            return 1 if rb.turn == WHITE else -1
        rb.push(mv)
    return terminal_result(rb, sl) or 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("rule", choices=["loss", "draw"])
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--depth", type=int, default=12)
    ap.add_argument("--extra", default="--colorsym --minsub=16 --bits=30 --threads=6")
    ap.add_argument("--side", default="auto", choices=["auto", "both", "white", "black"])
    args = ap.parse_args()
    sl = args.rule == "loss"
    server = Server(args.n, args.rule, args.extra.split())
    vwhite = server.value
    engine = open_stockfish()
    limit = chess.engine.Limit(depth=args.depth)
    # "auto": the tablebase plays a side it is not theoretically losing from -- the
    # winner's side if decisive, else White (a draw). This is the side on which a
    # perfect player must never lose.
    if args.side == "auto":
        sides = [(WHITE if vwhite >= 0 else BLACK, "W" if vwhite >= 0 else "B")]
    elif args.side == "both":
        sides = [(WHITE, "W"), (BLACK, "B")]
    else:
        sides = [(WHITE, "W")] if args.side == "white" else [(BLACK, "B")]
    try:
        for side, name in sides:
            gval = vwhite if side == WHITE else -vwhite
            W = D = L = 0
            for g in range(args.games):
                res = play_game(server, args.n, sl, side, engine, limit, (g + 1) * 2654435761 & 0xFFFFFFFFFFFF)
                ours = res if side == WHITE else -res
                if ours > 0: W += 1
                elif ours == 0: D += 1
                else: L += 1
                assert ours >= gval, (args.n, args.rule, name, g, ours, gval)
            flag = "" if (gval < 0 or L == 0) else "  <-- LOSS ON NON-LOSING SIDE!"
            print("%d %-4s %s theory=%+d  W=%d D=%d L=%d%s" % (args.n, args.rule, name, gval, W, D, L, flag), flush=True)
    finally:
        engine.quit()
        server.close()


if __name__ == "__main__":
    main()
