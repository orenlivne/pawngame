"""An interface of pawn boards."""


class PawnBoard:
    """An interface of pawn boards."""
    def key(self):
        """Returns a board hash. Used as a memo key."""
        raise ValueError("Must be implemented by sub-classes")

    def legal_moves(self):
        """Returns the list of legal moves."""
        raise ValueError("Must be implemented by sub-classes")

    def has_legal_moves(self) -> bool:
        """Returns True iff there is a legal move. Could be faster than calling len(legal_moves()) > 0."""
        raise ValueError("Must be implemented by sub-classes")

    def push(self, move):
        """Makes the move 'move'."""
        raise ValueError("Must be implemented by sub-classes")

    def pop(self):
        """Undoes the last move."""
        raise ValueError("Must be implemented by sub-classes")

    def move_stack(self):
        """Returns a board hash. Used as a memo key."""
        raise ValueError("Must be implemented by sub-classes")

    def has_legal_en_passant(self) -> bool:
        """Returns True iff there is a legal en passant in the position."""
        raise ValueError("Must be implemented by sub-classes")

    def encode_move(self, move) -> str:
        """
        Returns a string representation of a move to be stored in a move tree memo.
        :param move: chess move object.
        :return: the string representation of a move."""
        raise ValueError("Must be implemented by sub-classes")

    def to_uci(self, move) -> str:
        """
        Returns a UCI string for the move.
        For example, a move from a7 to a8 would be a7a8 or a7a8q (if the latter is a promotion to a queen).
        The UCI representation of a null move is 0000.
        :param move: chess move object.
        :return: UCI string.
        """
        raise ValueError("Must be implemented by sub-classes")
