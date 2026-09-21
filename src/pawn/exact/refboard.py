"""Reference pawn-game board.

An independent, clarity-first 8x8 pawn move generator for the "pawn game"
(pawns only, no kings). It is deliberately simple so it can serve as the
*correctness oracle* for the fast solvers: its legal-move generation is
fuzz-tested square-for-square against python-chess on kingless boards.

Board / square convention matches python-chess: files a..h = 0..7, ranks
1..8 = 0..7, ``square = rank * 8 + file`` (a1 = 0, h1 = 7, a8 = 56, h8 = 63).

Rules implemented (see README of adanhammod/pawn-game):
  * pawns push one square forward onto an empty square;
  * a pawn on its starting rank may push two squares if both are empty;
  * pawns capture diagonally forward;
  * en passant, exactly as in chess;
  * reaching the last rank ("touchdown"), capturing the opponent's last pawn,
    or leaving the opponent with no legal move are the three ways to win.

The stalemate convention (no legal move => loss for the side to move, vs. draw)
is *not* decided here -- the board only reports the facts; the solver applies
the chosen ruleset.
"""

WHITE, BLACK = 0, 1

FULL = (1 << 64) - 1
FILE_A = 0x0101010101010101
FILE_H = 0x8080808080808080
RANK_1 = 0x00000000000000FF
RANK_2 = 0x000000000000FF00
RANK_7 = 0x00FF000000000000
RANK_8 = 0xFF00000000000000

_FILES = "abcdefgh"


def sq(file: int, rank: int) -> int:
    return rank * 8 + file


def sq_file(s: int) -> int:
    return s & 7


def sq_rank(s: int) -> int:
    return s >> 3


def square_name(s: int) -> str:
    return _FILES[s & 7] + str((s >> 3) + 1)


def bits(mask: int):
    """Yields the index of each set bit, lowest first."""
    while mask:
        lsb = mask & (-mask)
        yield lsb.bit_length() - 1
        mask ^= lsb


def popcount(mask: int) -> int:
    return bin(mask).count("1")


class RefBoard:
    """A minimal, obviously-correct pawn-game board.

    A move is a 3-tuple ``(from_square, to_square, is_en_passant)``.  A move
    whose ``to_square`` lies on the last rank for the mover is a *touchdown*
    (an immediate win); the board still generates it as an ordinary move and it
    is up to the solver to recognise it.
    """

    __slots__ = ("wp", "bp", "turn", "ep_sq", "_stack")

    def __init__(self, wp: int = 0, bp: int = 0, turn: int = WHITE, ep_sq=None):
        self.wp = wp
        self.bp = bp
        self.turn = turn
        self.ep_sq = ep_sq
        self._stack = []

    # ------------------------------------------------------------------ setup
    @classmethod
    def from_fen(cls, fen: str) -> "RefBoard":
        """Parses a (kingless) FEN. Kings, if present, are ignored."""
        parts = fen.split()
        placement = parts[0]
        turn = WHITE
        ep_sq = None
        if len(parts) >= 2:
            turn = WHITE if parts[1] == "w" else BLACK
        if len(parts) >= 4 and parts[3] != "-":
            f = _FILES.index(parts[3][0])
            r = int(parts[3][1]) - 1
            ep_sq = sq(f, r)

        wp = bp = 0
        rank = 7
        file = 0
        for ch in placement:
            if ch == "/":
                rank -= 1
                file = 0
            elif ch.isdigit():
                file += int(ch)
            elif ch in "Pp":
                s = sq(file, rank)
                if ch == "P":
                    wp |= 1 << s
                else:
                    bp |= 1 << s
                file += 1
            elif ch in "Kk":
                file += 1  # ignore kings
            else:
                raise ValueError("unsupported FEN piece %r in %r" % (ch, fen))
        b = cls(wp, bp, turn, ep_sq)
        b._canonicalize_ep()
        return b

    def _canonicalize_ep(self):
        """Drop the ep square unless the side to move can actually capture on it.

        This keeps transposition keys tight: two positions that differ only in an
        *unusable* en-passant flag must share a key.
        """
        if self.ep_sq is None:
            return
        if not self._ep_capturers():
            self.ep_sq = None

    def _ep_capturers(self):
        """List of own pawns that could capture en passant on ``self.ep_sq``."""
        if self.ep_sq is None:
            return []
        me = self.wp if self.turn == WHITE else self.bp
        opp = self.bp if self.turn == WHITE else self.wp
        d = 8 if self.turn == WHITE else -8
        # The pawn to be captured sits one rank behind the ep target (the square
        # the double-pushed pawn landed on). No pawn there => not a real ep.
        if not (opp & (1 << (self.ep_sq - d))):
            return []
        out = []
        for df in (-1, 1):
            frm = self.ep_sq - d - df
            if 0 <= frm < 64 and abs(sq_file(frm) - sq_file(self.ep_sq)) == 1:
                if me & (1 << frm):
                    out.append(frm)
        return out

    # ------------------------------------------------------------- accessors
    def key(self):
        """Hashable transposition key: (white pawns, black pawns, turn, ep)."""
        return (self.wp, self.bp, self.turn, self.ep_sq)

    def my_pawns(self) -> int:
        return self.wp if self.turn == WHITE else self.bp

    def opp_pawns(self) -> int:
        return self.bp if self.turn == WHITE else self.wp

    @staticmethod
    def is_touchdown(move) -> bool:
        r = sq_rank(move[1])
        return r == 0 or r == 7

    # -------------------------------------------------------- move generation
    def legal_moves(self):
        """Returns the list of legal moves for the side to move."""
        me = self.wp if self.turn == WHITE else self.bp
        opp = self.bp if self.turn == WHITE else self.wp
        occ = self.wp | self.bp
        empty = FULL ^ occ
        d = 8 if self.turn == WHITE else -8
        start_rank = 1 if self.turn == WHITE else 6

        moves = []
        for frm in bits(me):
            f = frm & 7
            one = frm + d
            if empty & (1 << one):
                moves.append((frm, one, False))
                if (frm >> 3) == start_rank:
                    two = frm + 2 * d
                    if empty & (1 << two):
                        moves.append((frm, two, False))
            # diagonal captures
            if f > 0:
                to = one - 1
                if opp & (1 << to):
                    moves.append((frm, to, False))
            if f < 7:
                to = one + 1
                if opp & (1 << to):
                    moves.append((frm, to, False))
        # en passant
        for frm in self._ep_capturers():
            moves.append((frm, self.ep_sq, True))
        return moves

    def has_legal_moves(self) -> bool:
        me = self.wp if self.turn == WHITE else self.bp
        opp = self.bp if self.turn == WHITE else self.wp
        occ = self.wp | self.bp
        empty = FULL ^ occ
        d = 8 if self.turn == WHITE else -8
        for frm in bits(me):
            f = frm & 7
            one = frm + d
            if empty & (1 << one):
                return True
            if f > 0 and (opp & (1 << (one - 1))):
                return True
            if f < 7 and (opp & (1 << (one + 1))):
                return True
        if self._ep_capturers():
            return True
        return False

    # -------------------------------------------------------------- make/undo
    def push(self, move):
        frm, to, is_ep = move
        white = self.turn == WHITE
        d = 8 if white else -8
        prev_ep = self.ep_sq

        if white:
            self.wp = (self.wp & ~(1 << frm)) | (1 << to)
        else:
            self.bp = (self.bp & ~(1 << frm)) | (1 << to)

        captured_sq = None
        if is_ep:
            captured_sq = to - d
        elif (self.bp if white else self.wp) & (1 << to):
            captured_sq = to
        if captured_sq is not None:
            if white:
                self.bp &= ~(1 << captured_sq)
            else:
                self.wp &= ~(1 << captured_sq)

        # New en-passant square: only set when an opposing pawn can actually
        # capture, so equivalent positions share a key.
        new_ep = None
        if abs(to - frm) == 16:
            skipped = frm + d
            opp = self.bp if white else self.wp
            tf = to & 7
            for adj in (to - 1, to + 1):
                if 0 <= adj < 64 and abs((adj & 7) - tf) == 1 and (opp & (1 << adj)):
                    new_ep = skipped
                    break
        self.ep_sq = new_ep

        self._stack.append((frm, to, is_ep, captured_sq, prev_ep))
        self.turn = BLACK if white else WHITE

    def pop(self):
        frm, to, is_ep, captured_sq, prev_ep = self._stack.pop()
        self.turn = BLACK if self.turn == WHITE else WHITE
        white = self.turn == WHITE

        if white:
            self.wp = (self.wp & ~(1 << to)) | (1 << frm)
        else:
            self.bp = (self.bp & ~(1 << to)) | (1 << frm)

        if captured_sq is not None:
            if white:
                self.bp |= (1 << captured_sq)
            else:
                self.wp |= (1 << captured_sq)

        self.ep_sq = prev_ep

    # ---------------------------------------------------------------- display
    def fen(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            row = ""
            empty = 0
            for file in range(8):
                s = sq(file, rank)
                ch = None
                if self.wp & (1 << s):
                    ch = "P"
                elif self.bp & (1 << s):
                    ch = "p"
                if ch is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += ch
            if empty:
                row += str(empty)
            rows.append(row)
        placement = "/".join(rows)
        turn = "w" if self.turn == WHITE else "b"
        ep = square_name(self.ep_sq) if self.ep_sq is not None else "-"
        return "%s %s - %s 0 1" % (placement, turn, ep)

    def __repr__(self):
        rows = []
        for rank in range(7, -1, -1):
            row = []
            for file in range(8):
                s = sq(file, rank)
                if self.wp & (1 << s):
                    row.append("P")
                elif self.bp & (1 << s):
                    row.append("p")
                else:
                    row.append(".")
            rows.append(" ".join(row))
        return "\n".join(rows) + ("\n%s to move" % ("W" if self.turn == WHITE else "B"))
