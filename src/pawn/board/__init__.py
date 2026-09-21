from . import pawn_board, _delegating_pawn_board, _compact_pawn_board

def create_board(board_type, fen) -> pawn_board.PawnBoard:
    """
    Returns a pawn board. A factory method.
    :param board_type: board type.
    :param fen: Initial board position FEN.
    :return: board object.
    """
    if board_type == "python-chess":
        return _delegating_pawn_board.DelegatingPawnBoard(fen)
    if board_type == "compact":
        return _compact_pawn_board.CompactPawnBoard(fen)
    else:
        raise ValueError("Unsupported board type '{}'".format(board_type))
