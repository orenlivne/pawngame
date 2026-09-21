"""A pawn board implementation that delegates to a python-chess Board."""
import chess
import chess.pgn
from typing import Optional
from . import pawn_board


class DelegatingPawnBoard(pawn_board.PawnBoard):
    """A pawn board implementation that delegates to a python-chess Board."""
    def __init__(self, fen):
        self._board = chess.Board(fen)

    def key(self):
        """Returns a hash of the board. This is a tuple comprising of
            - White pawn location mask.
            - Black pawn location mask.
            - Side to move.
            - En-passant square on the 3rd or 6th rank, if exists by FEN rules.
        """
        board = self._board
        # Faster hash, yet can still be encoded with far less bits (pack turn, enpassant, 6x8 squares only).
        ep_square = board.ep_square if self.has_legal_en_passant() else None
        return board.pawns & board.occupied_co[chess.WHITE], \
               board.pawns & board.occupied_co[chess.BLACK], \
               board.turn, \
               ep_square

    def encode_move(self, move: chess.Move) -> Optional[str]:
        """
        Returns a UCI string for the move, which is its string representation here.
        For example, a move from a7 to a8 would be a7a8 or a7a8q (if the latter is a promotion to a queen).
        The UCI representation of a null move is 0000.
        :param move: chess move object.
        :return: the UCI string for the move."""
        return move.uci() if move is not None else None

    def from_encoded(self, move_uci) -> chess.Move:
        return chess.Move.from_uci(move_uci)

    def to_uci(self, move):
        return str(move)

    def fen(self):
        return self._board.fen()

    def legal_moves(self):
        return self._board.legal_moves

    def has_legal_moves(self) -> bool:
        return self._board.legal_moves.count() != 0

    def push(self, move):
        self._board.push(move)

    def pop(self):
        return self._board.pop()

    def move_stack(self):
        return self._board.move_stack

    def has_legal_en_passant(self):
        return self._board.has_legal_en_passant()

    def evaluate(self):
        return _Evaluator(self._board).evaluate()


class _Evaluator:
    def __init__(self, board: chess.Board):
        self.board = board
        self.my_pieces = board.pieces(piece_type=chess.PAWN, color=board.turn)
        self.opponent_pieces = board.pieces(piece_type=chess.PAWN, color=(not board.turn))

    def evaluate(self):
        # Note: uses the assumption that there always has to be material on the board. So can't have a situation where
        # there are no white pieces AND no black pieces, only one or the other.
        if not self.my_pieces:
            return -1
        if not self.opponent_pieces:
            return 1

        # If we have a pawn on the 7th, it's a win.
        my_steps_to_promotion = self.min_steps_to_promotion(self.board.turn)
        if 1 <= my_steps_to_promotion <= 2:
            return 1

        # Otherwise, the presence of captures complicates the evaluation as pawns can disappear. Thus, if the side to
        # move has a capture, return an inconclusive result. That automatically covers enpassants.
        if any(self.board.generate_legal_captures()):
            return None

        # Compare our most advanced passer with the opponents'.
        opponent_steps_to_promotion = self.min_steps_to_promotion(not self.board.turn)

        # No passed pawns, inconclusive result.
        if not my_steps_to_promotion and not opponent_steps_to_promotion:
            return None
        # We have a passed pawn and he doesn't, win.
        if my_steps_to_promotion and not opponent_steps_to_promotion:
            return 1
        # He has a passed pawn and we don't. Even though it's us to move, still a loss.
        if not my_steps_to_promotion and opponent_steps_to_promotion:
            return -1

        # Check which passed pawn edges the other (includes the case where one side has a passer and the other doesn't).
        # If both passers are the same # squares from promotion, we win since it's our move.
        return 1 if my_steps_to_promotion <= opponent_steps_to_promotion else -1

    def min_steps_to_promotion(self, side):
        if side == self.board.turn:
            return self._min_steps_to_promotion(self.board.turn, self.my_pieces, self.opponent_pieces,
                                                self.board.ep_square)
        return self._min_steps_to_promotion(not self.board.turn, self.opponent_pieces, self.my_pieces,
                                            self.board.ep_square)

    def _min_steps_to_promotion(self, side, my_pieces, opponent_pieces, ep_square):
        passer_ranks = filter(lambda steps: steps > 0,
                              (_num_steps_to_promotion(
                                  self.board, square, self.board.turn, side, opponent_pieces, ep_square)
                               for square in my_pieces))
        return min(passer_ranks, default=0)


def _num_steps_to_promotion(board, square, turn, color, opponent_pieces, ep_square):
    """Returns the number of moves to promote if there's a passed pawn on 'square', else 0."""
    direction = 1 if color == chess.WHITE else -1
    # passer_via_capture = False
    # if color != turn:
    #     # We are considering an opponent pawn. If it can be captured by the side to move, it's not a passer.
    #     if any(board.attackers(turn, square)):
    #         return 0
    #     # An opponent pawn that jumped twice and can be captured en passant.
    #     if ep_square is not None and ep_square == square - 8 * direction:
    #         return 0
    #
    clear_path = _is_path_clear(color, square, opponent_pieces)
    rank = square // 8
    # if color == turn:
    #     # Side to move can also capture on this next move, possibly creating a passer then.
    #
    #     # If it's our turn and there's an en passant possibility, add it to the set of opponent piece squares
    #     # because we can capture on it.
    #     if ep_square is not None:
    #         opponent_pieces |= chess.SquareSet([ep_square])
    #
    #     # Has a capture to the left.
    #     if square % 8 > 0:
    #         capture_square = 8 * (rank + direction) + square % 8 - 1
    #         if opponent_pieces & chess.SquareSet([capture_square]):
    #             clear_path_via_capture = _is_path_clear(color, capture_square, opponent_pieces)
    #             clear_path |= clear_path_via_capture
    #             if clear_path_via_capture:
    #                 passer_via_capture = True
    #     # Has capture to the right.
    #     if square % 8 < 7:
    #         capture_square = 8 * (rank + direction) + square % 8 + 1
    #         if opponent_pieces & chess.SquareSet([capture_square]):
    #             clear_path_via_capture = _is_path_clear(color, capture_square, opponent_pieces)
    #             clear_path |= clear_path_via_capture
    #             if clear_path_via_capture:
    #                 passer_via_capture = True
    if clear_path:
        if ((color == chess.WHITE) and (rank == 1)) or ((color == chess.BLACK) and (rank == 6)):
            # Double jump, reduce #steps to promotion by 1.
            rank += direction
        return 7 - rank if color == chess.WHITE else rank
    else:
        return 0


def _is_path_clear(color, square, opponent_pieces):
    """Returns True if and only if a pawn of color 'side' is a guaranteed passer."""
    return not _PAWN_OBSTACLE_SQUARES[color][square] & opponent_pieces


def _pawn_obstacle_squares(square, color):
    direction = 1 if color == chess.WHITE else -1
    limit = 56 if color == chess.WHITE else 7
    # The file part ahead of the square.
    for x in range(square + 8 * direction, limit, 8 * direction): yield x
    if square % 8 > 0:
        for x in range(square + 8 * direction - 1, limit, 8 * direction): yield x
    if square % 8 < 7:
        for x in range(square + 8 * direction + 1, limit, 8 * direction): yield x


# Cache the obstacles of each square.
_PAWN_OBSTACLE_SQUARES = [[chess.SquareSet(_pawn_obstacle_squares(square, side))
                           for square in range(64)] for side in (chess.BLACK, chess.WHITE)]


#------------------------------------------------------------------------------------------------
# TODO(oren): memoization optimization - integrate into board API so pawn solver can call these.
#------------------------------------------------------------------------------------------------

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
#     # TODO: fix
#     board = chess.Board(epd)
#     pawns = board.pawns
#     left_margin = next(itertools.dropwhile(lambda x: x[1], enumerate(pieces & r == 0 for r in chess.BB_FILES)))[0]
#     right_margin = next(itertools.dropwhile(lambda x: x[1], enumerate(pieces & r == 0 for r in chess.BB_FILES[::-1])))[0]
#     for num_files in itertools.chain(range(-left_margin, 0), range(1, right_margin + 1)):
#         yield _shift_lr_by(epd, num_files)
