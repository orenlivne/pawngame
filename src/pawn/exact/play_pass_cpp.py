"""Tablebase-vs-Stockfish play-test for the *pass* rule variant.

Same never-lose check as play_batch_cpp, but for the variant where a player may pass
unless the opponent just passed. The C++ move server is queried with the pass-right
(``cp 0``/``cp 1``) before each position and may answer ``pass``; Stockfish never
passes (it only makes real pawn moves, and is forced to pass only when it has no
pawn move), which merely makes it a weaker opponent -- the perfect tablebase must
still never lose. Terminal rules match the solver exactly.
"""
from __future__ import annotations

import argparse
import subprocess
import os

import chess.engine

from .refboard import RefBoard, WHITE, BLACK
from .positions import pawn_game_fen
from .play_stockfish import open_stockfish
from .play_batch import sf_move_fast

CPP = os.environ.get("PAWN_SRV", os.path.join(os.path.dirname(__file__), "..", "..", "cpp", "pawnsolver_par"))


class Server:
    def __init__(self, n, rule, extra):
        self.p = subprocess.Popen([CPP, str(n), rule, "--serve"] + extra,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.value = None
        for line in self.p.stdout:
            if line.startswith("n="):
                self.value = int(line.split("value=")[1].split()[0])
            if line.strip() == "READY":
                break

    def seed(self, s):
        self.p.stdin.write("seed %d\n" % s); self.p.stdin.flush(); self.p.stdout.readline()

    def move(self, rb, canpass):
        self.p.stdin.write("cp %d\n" % (1 if canpass else 0)); self.p.stdin.flush(); self.p.stdout.readline()
        self.p.stdin.write(rb.fen() + "\n"); self.p.stdin.flush()
        return self.p.stdout.readline().strip()

    def close(self):
        try:
            self.p.stdin.write("quit\n"); self.p.stdin.flush()
        except Exception:  # noqa: BLE001
            pass
        self.p.terminate()


def pass_terminal(rb, canpass, sl):
    """White-POV terminal value, or None if the position is not terminal."""
    if rb.wp == 0:
        return -1
    if rb.bp == 0:
        return 1
    if not rb.legal_moves() and not canpass:      # no pawn move and cannot pass
        if not sl:
            return 0
        return -1 if rb.turn == WHITE else 1
    return None


def _apply_pass(rb):
    rb.turn ^= 1
    rb.ep_sq = None


def play_game(server, n, sl, our_side, engine, limit, gseed):
    server.seed(gseed)
    rb = RefBoard.from_fen(pawn_game_fen(n))
    canpass = True
    for _ in range(800):
        t = pass_terminal(rb, canpass, sl)
        if t is not None:
            return t
        pawn_moves = rb.legal_moves()
        if rb.turn == our_side:
            reply = server.move(rb, canpass)
            if reply == "pass":
                _apply_pass(rb); canpass = False; continue
            if reply in ("terminal", "none"):
                return pass_terminal(rb, canpass, sl) or 0
            frm = "abcdefgh".index(reply[0]) + 8 * (int(reply[1]) - 1)
            to = "abcdefgh".index(reply[2]) + 8 * (int(reply[3]) - 1)
            mv = next(m for m in pawn_moves if m[0] == frm and m[1] == to)
            if RefBoard.is_touchdown(mv):
                return 1 if rb.turn == WHITE else -1
            rb.push(mv); canpass = True
        else:
            if pawn_moves:                        # Stockfish plays a real pawn move
                mv = sf_move_fast(engine, rb, limit)
                if RefBoard.is_touchdown(mv):
                    return 1 if rb.turn == WHITE else -1
                rb.push(mv); canpass = True
            else:                                  # no pawn move but canpass -> forced pass
                _apply_pass(rb); canpass = False
    return pass_terminal(rb, canpass, sl) or 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("rule", choices=["loss", "draw"])
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--depth", type=int, default=12)
    ap.add_argument("--extra", default="--pass --colorsym --minsub=16 --bits=28 --threads=6")
    ap.add_argument("--side", default="auto", choices=["auto", "both", "white", "black"])
    args = ap.parse_args()
    sl = args.rule == "loss"
    extra = args.extra.split()
    if "--pass" not in extra:
        extra = ["--pass"] + extra
    server = Server(args.n, args.rule, extra)
    vwhite = server.value
    engine = open_stockfish()
    limit = chess.engine.Limit(depth=args.depth)
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
            print("%d %-4s pass %s theory=%+d  W=%d D=%d L=%d%s" % (args.n, args.rule, name, gval, W, D, L, flag), flush=True)
    finally:
        engine.quit()
        server.close()


if __name__ == "__main__":
    main()
