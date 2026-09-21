"""Canonical starting positions for the n-vs-n pawn game.

For n < 8 the pawns are *left-justified* (files a..n) by default, per the
project spec.  Note this is a genuine choice, not a symmetry: a block touching
the a-file plays differently from a centered block, because the edge pawn has
only one capture direction and different passer geometry.  ``justify`` lets you
ask for the centered or right layout for comparison.
"""


def pawn_game_fen(num_pawns: int, justify: str = "left") -> str:
    """FEN for the n-vs-n pawn game start (White to move), kingless.

    White pawns on rank 2, Black pawns on rank 7, on the same ``num_pawns``
    adjacent files.
    """
    if not 1 <= num_pawns <= 8:
        raise ValueError("num_pawns must be in 1..8, got %d" % num_pawns)
    space = 8 - num_pawns
    if justify == "left":
        left = 0
    elif justify == "right":
        left = space
    elif justify == "center":
        left = space // 2
    else:
        raise ValueError("justify must be left/right/center, got %r" % justify)
    right = space - left

    def row(symbol):
        s = ""
        if left:
            s += str(left)
        s += symbol * num_pawns
        if right:
            s += str(right)
        return s

    ranks = ["8", row("p"), "8", "8", "8", "8", row("P"), "8"]
    return "/".join(ranks) + " w - - 0 1"


# Convenience constants for the left-justified games.
PAWN_GAME_FEN = {n: pawn_game_fen(n) for n in range(1, 9)}
