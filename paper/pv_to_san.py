"""Convert solver `--pv` output into readable SAN-style move lists (and per-ply
FENs, for choosing diagram positions).

Reads the C++ solver's stdout blocks:
    n=<N> rule=<loss|draw> ... value=<v> (<LABEL>) ...
    optimal_first_moves: <uci> <uci> ...
    pv: <uci> <uci> ...
and emits, per (n, rule): the value, the optimal first moves in SAN, the PV in
SAN with White's moves numbered, and the FEN after each ply.

Pawn-game SAN: a straight push is its destination (b4); a diagonal move is a
capture, written <from-file>x<dest> (cxd5), with " e.p." appended for en
passant; a move to the last rank is a touchdown, marked with the destination and
a double dagger.
"""
import re
import sys

sys.path.insert(0, "/Users/oren/code/chess/pawngame/src")
from pawn.exact.refboard import RefBoard, square_name, sq_file
from pawn.exact.positions import pawn_game_fen

_LABEL = {1: "White wins", -1: "Black wins", 0: "Draw"}


def uci_to_move(board, uci):
    frm = "abcdefgh".index(uci[0]) + 8 * (int(uci[1]) - 1)
    to = "abcdefgh".index(uci[2]) + 8 * (int(uci[3]) - 1)
    for m in board.legal_moves():
        if m[0] == frm and m[1] == to:
            return m
    raise ValueError("illegal pv move %s in %s" % (uci, board.fen()))


def move_san(board, m):
    frm, to, is_ep = m
    dest = square_name(to)
    touchdown = RefBoard.is_touchdown(m)
    if sq_file(frm) != sq_file(to):  # diagonal = capture
        san = "%sx%s" % ("abcdefgh"[sq_file(frm)], dest)
        if is_ep:
            san += "\\,e.p."
    else:
        san = dest
    if touchdown:
        san += "$\\ddagger$"
    return san


def pv_to_san(n, uci_moves):
    board = RefBoard.from_fen(pawn_game_fen(n))
    out = []
    fens = [board.fen()]
    for i, uci in enumerate(uci_moves):
        m = uci_to_move(board, uci)
        san = move_san(board, m)
        if board.turn == 0:  # White
            out.append("%d.\\,%s" % (i // 2 + 1, san))
        else:
            out.append(san)
        board.push(m)
        fens.append(board.fen())
    return " ".join(out), fens


def first_moves_san(n, uci_list):
    board = RefBoard.from_fen(pawn_game_fen(n))
    return ", ".join(move_san(board, uci_to_move(board, u)) for u in uci_list)


def parse(text):
    """Yield (n, rule, value, first_moves_uci, pv_uci)."""
    blocks = re.findall(
        r"n=(\d+) rule=(\w+).*?value=(-?\d+).*?\n(?:optimal_first_moves: (.*)\n)?(?:pv: (.*)\n)?",
        text)
    for n, rule, v, fm, pv in blocks:
        yield int(n), rule, int(v), (fm or "").split(), (pv or "").split()


if __name__ == "__main__":
    text = sys.stdin.read() if len(sys.argv) < 2 else open(sys.argv[1]).read()
    for n, rule, v, fm, pv in parse(text):
        if not pv:
            continue
        san, fens = pv_to_san(n, pv)
        fm_san = first_moves_san(n, fm) if fm else ""
        print("=== n=%d %s: %s ===" % (n, rule, _LABEL[v]))
        print("first moves: %s" % fm_san)
        print("PV: %s" % san)
        print("final FEN: %s" % fens[-1])
        print()
