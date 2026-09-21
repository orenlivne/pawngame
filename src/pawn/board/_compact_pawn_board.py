"""A compact pawn game board object. Uses bitwise operations to describe squares and moves directly to save time and
space."""
import chess
import functools
import re
from . import pawn_board
from operator import ior
# TODO(oren): experiment with numpy data types - are they faster with bitwise operations?
#from numpy import int8, int64


# Note: opposite notation of python-chess.
COLORS = [WHITE, BLACK] = [False, True]

# Game board notation.
# TODO(oren): maybe switch to int8 if it's faster.
Square = int

RANKS, FILES = 6, 8
BOARD_SIZE = RANKS * FILES
FILES_1 = FILES - 1

# Useful notation congruent to the usual 8x8 chess board.
SQUARES = [
    A2, B2, C2, D2, E2, F2, G2, H2,
    A3, B3, C3, D3, E3, F3, G3, H3,
    A4, B4, C4, D4, E4, F4, G4, H4,
    A5, B5, C5, D5, E5, F5, G5, H5,
    A6, B6, C6, D6, E6, F6, G6, H6,
    A7, B7, C7, D7, E7, F7, G7, H7,
] = list(range(BOARD_SIZE))

ALL_SQUARES = (1 << BOARD_SIZE) - 1

SQUARES = list(range(BOARD_SIZE))

"""Rank 1 (White) and rank 6 (Black) where the pawns initially stand."""
INITIAL_RANK = [(1 << 8) - 1, ((1 << 8) - 1) << (8 * 5)]


def _list_or(lst):
    return functools.reduce(ior, lst, 0)


def _to_mask(squares):
    return _list_or(map(lambda x: 1 << x, squares))


FILE_MASK = [None] * FILES
FILE_MASK[0] = _to_mask(range(0, BOARD_SIZE, RANKS))
for file in range(1, FILES):
    FILE_MASK[file] = FILE_MASK[file - 1] << 1
REVERSED_FILE_SHIFTS = list(range(FILES // 2 - 1, -(FILES // 2), -1))

# FEN parsing regular expressions.

FEN_CASTLING_REGEX = re.compile(r"^(?:-|[KQABCDEFGH]{0,2}[kqabcdefgh]{0,2})\Z")

FILE_NAMES = ["a", "b", "c", "d", "e", "f", "g", "h"]

RANK_NAMES = ["1", "2", "3", "4", "5", "6", "7", "8"]

SQUARE_NAMES = [f + r for r in RANK_NAMES for f in FILE_NAMES]

PAWN_SYMBOLS = "Pp"

# Only kings and pawns are supported. We added kings so that legal FEN positions are supported by our board.
PIECE_SYMBOLS = [None, "p", "k"]


class CompactPawnBoard(pawn_board.PawnBoard):
    """A pawn board implementation that does not depend on python-chess. Everything is implemented with compact bit
    masks."""
    def __init__(self, fen: str):
        # Location of white and black pieces - 8x6 bit masks (ranks 2-7).
        self._pieces = None
        self._clear_board()
        # Game move stack. Each move is a tuple (from_square, to_square, is_enpassant).
        self._move_stack = []
        # The side to move.
        self._turn = WHITE
        # The square on which we can capture enpassant, or None if such doesn't exist.
        self._ep_square = None
        if fen is not None:
            self._set_fen(fen)
        self._piece_set = [set(_find_set_bits(piece_mask)) for piece_mask in self._pieces]

    def fliplr_key(self):
        # Flip white pieces, black pieces, ep square.
        return fliplr_board(self._pieces[WHITE]), \
               fliplr_board(self._pieces[BLACK]), \
               self._turn, \
               FILES * (self._ep_square // FILES) + FILES_1 - (self._ep_square % FILES)

    @staticmethod
    def from_key(key):
        b = CompactPawnBoard(None)
        b._pieces = [key[0], key[1]]
        # Game move stack. Each move is a tuple (from_square, to_square, is_enpassant).
        b._move_stack = []
        b._turn = key[2]
        b._ep_square = key[3]
        return b

    def to_chess_board(self):
        """Converts a compact board to a python-chess Board."""
        b = chess.Board()
        b.clear_board()
        b.turn = not self._turn
        for color in (WHITE, BLACK):
            for square in SQUARES:
                if self._pieces[color] & (1 << square):
                    b.set_piece_at(square + 8, chess.Piece(chess.PAWN, not color))
        if self.has_legal_en_passant():
            b.ep_square = self._ep_square + 8
        return b

    def fen(self):
        return self.to_chess_board().fen()

    def __repr__(self):
        board = [8 * ["."] for _ in range(8)]
        for square in SQUARES:
            for color in COLORS:
                if self._pieces[color] & (1 << square):
                    board[square // 8 + 1][square % 8] = PAWN_SYMBOLS[color]
        return "\n".join(" ".join(rank) for rank in board[::-1])

    def key(self):
        """Returns a hash of the board."""
        # For now, saving the full 8x6 to eliminate possible bugs.
        # TODO(oren): Save only 8x5 masks since we know there's never going to be a pawn on the 7th rank, we will be
        # able to evaluate the position as a node state beforehand.
        return self._pieces[WHITE], \
               self._pieces[BLACK], \
               self._turn, \
               self._ep_square

    def legal_moves(self):
        """Returns the list of legal moves. A move is a tuple (from_square, to_square, is_enpassant)."""
        my_pieces, opponent_pieces = self._pieces[self._turn], self._pieces[not self._turn]
        direction = 1 if self._turn == WHITE else -1
        # All squares that are occupied by a pawn.
        occupied = self._pieces[WHITE] | self._pieces[BLACK]

        # Finding all moves is implemented in block/vectorized bit operations.
        # Sorting them in forcing order - captures, double jumps, single jumps to help prune more.

        # Captures.
        for move in self._generate_legal_captures():
            yield move

        # Double jumps.
        my_pieces_on_initial = my_pieces & INITIAL_RANK[self._turn]
        # Move back two ranks to align with the source pawn's square.
        offset = 8 * 2
        occupied_ahead = (occupied >> offset) if self._turn == WHITE else (occupied << offset)
        from_square = my_pieces_on_initial & ~occupied_ahead
        for bit in _find_set_bits(from_square):
            yield bit, bit + direction * offset, False

        # Single advances.
        # Move back one rank to align with the source pawn's square.
        offset = 8
        occupied_ahead = (occupied >> offset) if self._turn == WHITE else (occupied << offset)
        from_square = my_pieces & ~occupied_ahead
        for bit in _find_set_bits(from_square):
            yield bit, bit + direction * offset, False

    def _generate_legal_captures(self):
        # Captures. Squares ahead, diagonally-adjacent are +7 and +9 or -9 and -7 from the source square for white,
        # black, respectively.
        my_pieces, opponent_pieces = self._pieces[self._turn], self._pieces[not self._turn]
        direction = 1 if self._turn == WHITE else -1
        for offset in (7, 9):
            occupied_ahead = (opponent_pieces >> offset) if self._turn == WHITE else (opponent_pieces << offset)
            from_square = my_pieces & occupied_ahead
            for bit in _find_set_bits(from_square):
                yield bit, bit + direction * offset, False

        # If en passant is present, check which of our pawns can capture and return all of them (1 or 2).
        if self._ep_square is not None:
            capturing_pawns = my_pieces & \
                        ((1 << (self._ep_square - direction * 7)) | (1 << (self._ep_square - direction * 9)))
            for bit in _find_set_bits(capturing_pawns):
                yield bit, self._ep_square, True

    def _has_legal_captures(self) -> bool:
        """Returns True iff there are legal capture moves."""
        try:
            next(self._generate_legal_captures())
            return True
        except StopIteration:
            return False

    def has_legal_moves(self) -> bool:
        """Returns True iff there are legal moves."""
        try:
            next(self.legal_moves())
            return True
        except StopIteration:
            return False

    def push(self, move):
        """Makes a move on the board. Note: does not check for legality. Assumes the move is legal. This is faster
        and we know we only make legal moves since we generate them in a different part of the code; this is not a
        general-purpose API that needs to be defensive."""
        from_square, to_square, is_en_passant = move
        direction = 1 if self._turn == WHITE else -1

        # Clear the source square and occupy the target square.
        self._pieces[self._turn] &= ~(1 << from_square)
        if to_square < 0:
            a = 0
        self._pieces[self._turn] |= (1 << to_square)
        # If it's an en passant, clear the square on the previous rank from the target square (from the opponent's
        # viewpoint) from the opponent's piece.
        if is_en_passant:
            self._pieces[not self._turn] &= ~(1 << (to_square - 8 * direction))
        else:
            # Clear the target square from opponent pieces (covers captures; does nothing if it's not a capture).
            self._pieces[not self._turn] &= ~(1 << to_square)

        # Update the en passant state.
        # Save en passant state before move.
        old_ep_square = self._ep_square
        self._ep_square = None
        if to_square == from_square + direction * 8 * 2:
            # Double jump, check if there is an opponent pawn on either side of the target square.
            if self._pieces[not self._turn] & ((1 << (to_square - 1)) | (1 << (to_square + 1))):
                self._ep_square = from_square + direction * 8

        # Push move to the move stack.
        self._move_stack.append([move, old_ep_square])
        # Switch the side the move.
        self._turn = not self._turn

    def pop(self):
        """Undoes the last move and returns it."""
        # Pop move from the move stack.
        move, old_ep_square = self._move_stack.pop()
        # Switch the side the move.
        self._turn = not self._turn
        from_square, to_square, is_en_passant = move

        # Occupy the source square and clear the target square.
        self._pieces[self._turn] |= (1 << from_square)
        self._pieces[self._turn] &= ~(1 << to_square)

        if (from_square % 8) != (to_square % 8):
            # Capture ==> occupy the target square with an opponent pawn.
            if is_en_passant:
                # Target square was actually one rank forward from opponent's viewpoint.
                direction = 1 if self._turn == WHITE else -1
                self._pieces[not self._turn] |= (1 << (to_square - 8 * direction))
            else:
                self._pieces[not self._turn] |= (1 << to_square)

        # Restore the en passant state.
        self._ep_square = old_ep_square
        return move

    def move_stack(self):
        """Returns the game move stack."""
        return [m[0] for m in self._move_stack]

    def has_legal_en_passant(self):
        """Returns True iff there is a legal en passant in the position."""
        return self._ep_square is not None

    def evaluate(self):
        """Returns the evaluation of the current position, if we can determine it (-1, 0, or 1) or None if we can't."""
        return _Evaluator(self).evaluate()

    def encode_move(self, move):
        return move if move is not None else None

    def from_encoded(self, move_uci):
        return move_uci

    def to_uci(self, move):
        return chr(ord("a") + (move[0] % 8)) + str(2 + move[0] // 8) + \
               chr(ord("a") + (move[1] % 8)) + str(2 + move[1] // 8)

    def _set_fen(self, fen: str):
        """
        Parses a FEN and sets the position from it.

        :raises: :exc:`ValueError` if the FEN string is invalid.
        """
        parts = fen.split()

        # Board part.
        try:
            board_part = parts.pop(0)
        except IndexError:
            raise ValueError("empty fen")

        # Turn.
        try:
            turn_part = parts.pop(0)
        except IndexError:
            turn = WHITE
        else:
            if turn_part == "w":
                turn = WHITE
            elif turn_part == "b":
                turn = BLACK
            else:
                raise ValueError("expected 'w' or 'b' for turn part of fen: {}".format(fen))

        # Validate castling part.
        try:
            castling_part = parts.pop(0)
        except IndexError:
            pass
        else:
            if not FEN_CASTLING_REGEX.match(castling_part):
                raise ValueError("invalid castling part in fen: {}".format(fen))

        # En passant square.
        try:
            ep_part = parts.pop(0)
        except IndexError:
            ep_square = None
        else:
            try:
                ep_square = None if ep_part == "-" else SQUARE_NAMES.index(ep_part)
            except ValueError:
                raise ValueError("invalid en passant part in fen: {}".format(fen))

        # Check that the half-move part is valid.
        try:
            halfmove_part = parts.pop(0)
        except IndexError:
            pass
        else:
            try:
                halfmove_clock = int(halfmove_part)
            except ValueError:
                raise ValueError("invalid half-move clock in fen: {}".format(fen))

            if halfmove_clock < 0:
                raise ValueError("half-move clock cannot be negative: {}".format(fen))

        # Check that the full-move number part is valid.
        # 0 is allowed for compability, but later replaced with 1.
        try:
            full_move_part = parts.pop(0)
        except IndexError:
            pass
        else:
            try:
                full_move_number = int(full_move_part)
            except ValueError:
                raise ValueError("invalid full move number in fen: {}".format(fen))
            if full_move_number < 0:
                raise ValueError("full move number cannot be negative: {}".format(fen))

        # All parts should be consumed now.
        if parts:
            raise ValueError("fen string has more parts than expected: {}".format(fen))

        # Apply.
        self._turn = turn
        # Shift en passant square one rank back, since we start at rank 2.
        if ep_square is not None:
            self._ep_square = ep_square - 8
        # Validate the board part and set it.
        self._set_board_fen(board_part)

    def _set_board_fen(self, fen: str) -> None:
        # Compatibility with set_fen().
        fen = fen.strip()
        if " " in fen:
            raise ValueError("expected position part of fen, got multiple parts: {}".format(fen))

        # Ensure the FEN is valid.
        rows = fen.split("/")
        if len(rows) != 8:
            raise ValueError("expected 8 rows in position part of fen: {}".format(fen))

        # Validate each row.
        for row in rows:
            field_sum = 0
            previous_was_digit = False
            previous_was_piece = False

            for c in row:
                if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                    if previous_was_digit:
                        raise ValueError("two subsequent digits in position part of fen: {}".format(fen))
                    field_sum += int(c)
                    previous_was_digit = True
                    previous_was_piece = False
                elif c == "~":
                    if not previous_was_piece:
                        raise ValueError("'~' not after piece in position part of fen: {}".format(fen))
                    previous_was_digit = False
                    previous_was_piece = False
                elif c.lower() in PIECE_SYMBOLS:
                    field_sum += 1
                    previous_was_digit = False
                    previous_was_piece = True
                else:
                    raise ValueError("invalid character in position part of fen: {}. "
                                     "Note: only pawns and kings are supported, no other pieces allowed.".format(fen))

            if field_sum != 8:
                raise ValueError("expected 8 columns per row in position part of fen: {}".format(fen))

        # Clear the board.
        self._clear_board()

        # Put pieces on the board.
        square_index = 0
        for c in fen:
            if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                square_index += int(c)
            elif c in PAWN_SYMBOLS:
                color = WHITE if c.isupper() else BLACK
                # Shift square index one rank back, since FEN 8x8 numbering starts at rank 1 and our board starts at
                # rank 2. FEN is also top-down ordered while we are bottom-up ordered.
                our_square_index = 8 * (6 - (square_index // 8)) + (square_index % 8)
                square = 1 << our_square_index
                self._pieces[color] |= square
                square_index += 1

    def _clear_board(self):
        self._pieces = [0] * 2


NOT_PASSED = 8


class _Evaluator:
    def __init__(self, board: CompactPawnBoard):
        self.board = board
        self.turn = board._turn
        self.my_pieces, self.opponent_pieces = board._pieces[self.turn], board._pieces[not self.turn]

    def evaluate(self):
        # Note: uses the assumption that there always has to be material on the board. So can't have a situation where
        # there are no white pieces AND no black pieces, only one or the other.
        if not self.my_pieces:
            return -1
        if not self.opponent_pieces:
            return 1

        # If we have a pawn on the 7th, it's a win. But even on the 6th, if we can get to the 7th and its our turn.
        my_steps_to_promotion = self.min_steps_to_promotion(self.turn)
        if my_steps_to_promotion <= 1:
            return 1

        # Otherwise, the presence of captures complicates the evaluation as pawns can disappear. Thus, if the side to
        # move has a capture, return an inconclusive result. That automatically covers en passants.
        if self.board._has_legal_captures():
            return None

        # Compare our most advanced passer with the opponents'.
        opponent_steps_to_promotion = self.min_steps_to_promotion(not self.turn)

        # No passed pawns, inconclusive result.
        if my_steps_to_promotion == NOT_PASSED and opponent_steps_to_promotion == NOT_PASSED:
            return None
        # We have a passed pawn and he doesn't, win.
        if my_steps_to_promotion != NOT_PASSED and opponent_steps_to_promotion == NOT_PASSED:
            return 1
        # He has a passed pawn and we don't. Even though it's us to move, still a loss.
        if my_steps_to_promotion == NOT_PASSED and opponent_steps_to_promotion != NOT_PASSED:
            return -1

        # Check which passed pawn edges the other (includes the case where one side has a passer and the other
        # doesn't).
        # If both passers are the same # squares from promotion, we win since it's our move.
        return 1 if my_steps_to_promotion <= opponent_steps_to_promotion else -1

    def min_steps_to_promotion(self, side):
        if side == self.turn:
            return self._min_steps_to_promotion(self.turn, self.my_pieces, self.opponent_pieces)
        return self._min_steps_to_promotion(not self.turn, self.opponent_pieces, self.my_pieces)

    def _min_steps_to_promotion(self, side, my_pieces, opponent_pieces):
        passer_ranks = filter(lambda steps: steps != NOT_PASSED,
                              (_num_steps_to_promotion(square, side, opponent_pieces)
                               for square in _find_set_bits(my_pieces)))
        return min(passer_ranks, default=NOT_PASSED)


def _num_steps_to_promotion(square, color, opponent_pieces):
    """Returns the number of moves to promote if there's a passed pawn on 'square', else 0."""
    direction = 1 if color == WHITE else -1
    clear_path = _is_path_clear(color, square, opponent_pieces)
    rank = square // 8
    if clear_path:
        if ((color == WHITE) and (rank == 0)) or ((color == BLACK) and (rank == 5)):
            # Double jump, reduce #steps to promotion by 1.
            rank += direction
        return 5 - rank if color == WHITE else rank
    else:
        return NOT_PASSED


def _is_path_clear(color, square, opponent_pieces):
    """Returns True if and only if a pawn of color 'side' is a guaranteed passer."""
    return not _PAWN_OBSTACLE_SQUARES[color][square] & opponent_pieces


def _pawn_obstacle_squares(square, color):
    direction = 1 if color == WHITE else -1
    limit = BOARD_SIZE if color == WHITE else 0
    # The file part ahead of the square.
    for x in range(square + 8 * direction, limit, 8 * direction):
        yield x
    if square % 8 > 0:
        for x in range(square + 8 * direction - 1, limit, 8 * direction):
            yield x
    if square % 8 < 7:
        for x in range(square + 8 * direction + 1, limit, 8 * direction):
            yield x


# Cache the obstacle mask of each square.
_PAWN_OBSTACLE_SQUARES = [[_to_mask(_pawn_obstacle_squares(square, side)) for square in range(BOARD_SIZE)]
                          for side in COLORS]


"""
------------------------------------------------------------------------------------------------
 TODO(oren): memoization optimization - integrate into board API so pawn solver can call these.
------------------------------------------------------------------------------------------------
"""


def _flip_lr(epd):
    parts = epd.split(' ', maxsplit=1)
    return "/".join(rank[::-1] for rank in parts[0].split('/')) + " " + parts[1]


def _shift_rank(rank, num_files):
    sz = len(rank)
    if sz == 1:
        return rank  # "8"
    if num_files < 0:
        # Shift left. Assuming position's left margin >= -num_files.
        left_margin = int(rank[0])
        left_margin = str(left_margin + num_files) if left_margin > - num_files else ""
        right_margin = str(int(rank[-1]) - num_files if rank[-1].isdigit() else - num_files)
    else:
        # Shift right. Assuming position's right margin >= num_files.
        left_margin = str(int(rank[0]) + num_files if rank[0].isdigit() else num_files)
        right_margin = int(rank[-1])
        right_margin = str(right_margin - num_files) if right_margin > num_files else ""
    return left_margin + rank[1:-1] + right_margin


def _shift_lr_by(epd, num_files):
    parts = epd.split(' ', maxsplit=1)
    return "/".join(_shift_rank(rank, num_files) for rank in parts[0].split('/')) + " " + parts[1]


# def _shift_lr(epd):
#     """Generates all legal shifts of the position 'epd'."""
#     board = chess.Board(epd)
#     pawns = board.pawns
#     left_margin = next(itertools.dropwhile(lambda x: x[1], enumerate(pieces & r == 0 for r in chess.BB_FILES)))[0]
#     right_margin = next(itertools.dropwhile(lambda x: x[1],
#       enumerate(pieces & r == 0 for r in chess.BB_FILES[::-1])))[0]
#     for num_files in itertools.chain(range(-left_margin, 0), range(1, right_margin + 1)):
#         yield _shift_lr_by(epd, num_files)

def _find_set_bits(num):
    # for i in range(BOARD_SIZE):
    #     if num & (1 << i):
    #         yield i
    return (i for i in range(BOARD_SIZE) if num & (1 << i))


def fliplr_board(square_mask):
    return _list_or((f & square_mask) << shift if shift >= 0 else (f & square_mask) >> (-shift)
            for f, shift in zip(FILE_MASK, REVERSED_FILE_SHIFTS))
