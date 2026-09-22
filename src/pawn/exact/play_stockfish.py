"""Empirical check: the exact tablebase must never LOSE against Stockfish.

The pawn game has no kings, but Stockfish needs a legal chess position.  We use
Stockfish only as a *move evaluator* for its own side -- it never moves a king.
For each of Stockfish's legal pawn moves we build the child position, drop two
kings onto the (always empty in a non-terminal position) back ranks so the
position is legal, and let Stockfish score it; Stockfish plays the pawn move it
rates best.  Our side plays the true kingless-perfect move from the tablebase,
and terminals / scoring use the pawn-game rules -- so the kings never affect the
actual game, only Stockfish's opinion.

A perfectly-playing side can never lose to any opponent, so if our side ever
loses, the tablebase is wrong.  (Stockfish's strength only affects whether we
also win.)
"""
from __future__ import annotations

import argparse
import shutil

import chess
import chess.engine

from .refboard import RefBoard, WHITE, BLACK, square_name
from .fastsolver import FastSolver
from .positions import pawn_game_fen

# Common install locations plus PATH; /usr/games/stockfish is Debian/Ubuntu's.
STOCKFISH_PATHS = [
    shutil.which("stockfish"),
    "/opt/homebrew/bin/stockfish",
    "/usr/local/bin/stockfish",
    "/usr/games/stockfish",
    "/usr/bin/stockfish",
    "stockfish",
]


def open_stockfish():
    last = None
    for p in STOCKFISH_PATHS:
        if not p:
            continue
        try:
            return chess.engine.SimpleEngine.popen_uci(p)
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError("Stockfish not found: %s" % last)


def _rb_to_chess(rb: RefBoard) -> "chess.Board | None":
    """Build a legal python-chess Board from a (non-terminal) pawn position by
    adding kings on the empty back ranks; return None if no legal placement."""
    base = chess.Board.empty()
    for s in range(64):
        if rb.wp & (1 << s):
            base.set_piece_at(s, chess.Piece(chess.PAWN, chess.WHITE))
        elif rb.bp & (1 << s):
            base.set_piece_at(s, chess.Piece(chess.PAWN, chess.BLACK))
    base.turn = chess.WHITE if rb.turn == WHITE else chess.BLACK
    # White king on rank 1, black king on rank 8, not attacked, not adjacent.
    for wk in range(0, 8):
        for bk in range(56, 64):
            if abs((wk & 7) - (bk & 7)) <= 1 and abs((wk >> 3) - (bk >> 3)) <= 1:
                continue  # kings adjacent
            b = base.copy()
            b.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
            b.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
            if b.is_valid():
                return b
    return None


def stockfish_move(engine, rb: RefBoard, limit) -> tuple:
    """Return Stockfish's preferred legal pawn move (a RefBoard move tuple)."""
    moves = rb.legal_moves()
    best_mv, best_score = None, None
    for mv in moves:
        if RefBoard.is_touchdown(mv):
            return mv  # winning move; take it
        rb.push(mv)
        child = _rb_to_chess(rb)
        rb.pop()
        if child is None:
            score = 0
        else:
            info = engine.analyse(child, limit)
            # Score from the mover's perspective (side that just moved = rb.turn).
            pov = chess.WHITE if rb.turn == WHITE else chess.BLACK
            score = info["score"].pov(pov).score(mate_score=100000)
        if best_score is None or score > best_score:
            best_score, best_mv = score, mv
    return best_mv


def tablebase_move(solver: FastSolver, rb: RefBoard) -> tuple:
    """A perfect move: one whose child value equals this node's value."""
    target = solver.value(rb)
    best = None
    for mv in rb.legal_moves():
        if RefBoard.is_touchdown(mv):
            return mv
        rb.push(mv)
        cv = -solver.value(rb)
        rb.pop()
        if cv == target:
            return mv
        if best is None:
            best = mv
    return best  # fallback (shouldn't happen)


def terminal_result(rb: RefBoard, stalemate_is_loss: bool):
    """Return +1/0/-1 (White's perspective) if terminal, else None."""
    # A side with no pawns has lost.
    if rb.wp == 0:
        return -1
    if rb.bp == 0:
        return 1
    if not rb.has_legal_moves():
        if stalemate_is_loss:
            return -1 if rb.turn == WHITE else 1
        return 0
    return None


def play_game(n, stalemate_is_loss, our_side, engine, limit, justify="left", verbose=False):
    """Play one game; return result from White's perspective (+1/0/-1)."""
    solver = FastSolver(stalemate_is_loss=stalemate_is_loss)
    rb = RefBoard.from_fen(pawn_game_fen(n, justify))
    solver.value(rb)  # solve once
    ply = 0
    while ply < 200:
        term = terminal_result(rb, stalemate_is_loss)
        if term is not None:
            return term
        if rb.turn == our_side:
            mv = tablebase_move(solver, rb)
        else:
            mv = stockfish_move(engine, rb, limit)
        if RefBoard.is_touchdown(mv):
            winner = 1 if rb.turn == WHITE else -1
            if verbose:
                print("  %s touchdown %s%s" % ("W" if rb.turn == WHITE else "B",
                                               square_name(mv[0]), square_name(mv[1])))
            return winner
        rb.push(mv)
        ply += 1
    return terminal_result(rb, stalemate_is_loss) or 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--rule", choices=["loss", "draw"], default="loss")
    ap.add_argument("--depth", type=int, default=14)
    ap.add_argument("--justify", default="left")
    args = ap.parse_args()
    sl = args.rule == "loss"
    engine = open_stockfish()
    limit = chess.engine.Limit(depth=args.depth)
    # Game value from White's perspective.
    v_white = FastSolver(stalemate_is_loss=sl).value(RefBoard.from_fen(pawn_game_fen(args.n, args.justify)))
    try:
        for our_side, name in [(WHITE, "White"), (BLACK, "Black")]:
            res = play_game(args.n, sl, our_side, engine, limit, args.justify, verbose=True)
            ours = res if our_side == WHITE else -res            # our-perspective result
            g = v_white if our_side == WHITE else -v_white       # our-perspective game value
            # Perfect play guarantees AT LEAST the game value against any opponent.
            ok = ours >= g
            print("n=%d rule=%s tablebase=%s: theory=%+d result=%+d  %s" %
                  (args.n, args.rule, name, g, ours, "OK" if ok else "*** TABLEBASE BUG (did worse than theory) ***"))
            assert ok, "tablebase did worse than the game value -- bug!"
    finally:
        engine.quit()


if __name__ == "__main__":
    main()
