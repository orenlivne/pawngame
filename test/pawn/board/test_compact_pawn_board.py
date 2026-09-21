"""Pawn game solver unit tests. Test results against a python-chess board."""
import chess
import pytest
import pawn.board._compact_pawn_board as c


class TestCompactPawnBoard:
    @pytest.mark.parametrize("fen,move,move_san",
                             [
                                 # test_push_white_single_advance
                                 ("8/8/p1p5/pP6/2P5/8/8/8 w - - 0 1", (c.C4, c.C5, False), "c4c5"),
                                 # test_push_black_single_advance
                                 ("8/8/p1p5/pP6/2P5/8/8/8 b - - 0 1", (c.C6, c.C5, False), "c6c5"),
                                 # test_push_double_advance
                                 ("8/2ppp3/8/8/8/8/2PPP3/8 w - - 0 1", (c.C2, c.C4, False), "c2c4"),
                                 ("8/2ppp3/8/8/8/8/2PPP3/8 b - - 0 1", (c.D7, c.D5, False), "d7d5"),
                                 # Capture.
                                 ("8/8/p1p5/pP6/2P5/8/8/8 b - - 0 1", (c.C6, c.B5, False), "c6b5"),
                                 # White en-passant capture.
                                 ("8/8/3p1p2/2pP4/4P3/8/5P2/8 w - c6 0 1", (c.D5, c.C6, True), "d5c6"),
                                 # Black en-passant capture.
                                 ("8/2ppppp1/8/8/1pP3P1/8/1P1PPP2/8 b - c3 0 1", (c.B4, c.C3, True), "b4c3"),
                             ])
    def test_push_pop(self, fen, move, move_san):
        # fen = "8/8/p1p5/pP6/2P5/8/8/8 w - - 0 1"
        # . . . . . . . .
        # . . . . . . . .
        # p . p . . . . .
        # p P . . . . . .
        # . . P . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .

        # Construct a board and a corresponding python-chess Board and check that they are identical.
        board = c.CompactPawnBoard(fen)
        b = board.to_chess_board()
        b_from_fen = chess.Board(fen)
        assert b.fen() == b_from_fen.fen()        # Make the move on both boards.
        assert board.has_legal_en_passant() == b.has_legal_en_passant()
        if board.has_legal_en_passant():
            assert board._ep_square == b.ep_square - 8

        board.push(move)
        b.push_san(move_san)
        # Compact board does not keep track of move numbers, so reset the python-chess board move number.
        b.fullmove_number = 1

        # Check that both boards are the same after the move.
        assert board.move_stack() == [move]
        assert board.to_chess_board().fen() == b.fen()

        # Undo the move on both boards.
        popped_move = board.pop()
        assert popped_move == move
        b.pop()
        b.fullmove_number = 1

        # Check that both boards are the same after undoing the move.
        assert board.move_stack() == []
        assert board.to_chess_board().fen() == b.fen()

    def test_multiple_push_pop(self):
        # Using 3-pawn game as an example.
        # Construct a board and a corresponding python-chess Board and check that they are identical.
        fen = '8/2ppp3/8/8/8/8/2PPP3/8 w - - 0 1'
        board = c.CompactPawnBoard(fen)
        b = board.to_chess_board()
        b_from_fen = chess.Board(fen)
        assert(b.fen() == b_from_fen.fen())        # Make the move on both boards.

        moves = [
            ((c.C2, c.C3, False), "c2c3"),
            ((c.D7, c.D5, False), "d7d5"),
            ((c.E2, c.E4, False), "e2e4"),
            ((c.D5, c.E4, False), "d5e4"),
        ]

        for i, (move, move_san) in enumerate(moves, 1):
            board.push(move)
            b.push_san(move_san)
            # Compact board does not keep track of move numbers, so reset the python-chess board move number.
            b.fullmove_number = 1

            assert board.move_stack() == [m[0] for m in moves[:i]]
            assert board.to_chess_board().fen() == b.fen()

        for move in moves[::-1]:
            popped_move = board.pop()
            assert popped_move == move[0]
            b.pop()
            assert board.to_chess_board().fen() == b.fen()

    @pytest.mark.parametrize("fen",
                             [
                                 "8/8/p1p5/pP6/2P5/8/8/8 w - - 0 1",
                                 '8/1p6/3p4/1p6/4pP2/2P1P3/8/8 b - f3 0 1',
                            ])
    def test_push_pop_restores_en_passant_state(self, fen):
        board = c.CompactPawnBoard(fen)
        for move in board.legal_moves():
            board.push(move)
            board.pop()
            assert board.fen() == fen

    @pytest.mark.parametrize("fen",
                             [
                                 # test_push_white_single_advance
                                 "8/8/p1p5/pP6/2P5/8/8/8 w - - 0 1",
                                 # test_push_black_single_advance
                                 "8/8/p1p5/pP6/2P5/8/8/8 b - - 0 1",
                                 # test_push_double_advance
                                 "8/2ppp3/8/8/8/8/2PPP3/8 w - - 0 1",
                                 "8/2ppp3/8/8/8/8/2PPP3/8 b - - 0 1",
                                 # Capture.
                                 "8/8/p1p5/pP6/2P5/8/8/8 b - - 0 1",
                                 # White en-passant capture.
                                 "8/8/3p1p2/2pP4/4P3/8/5P2/8 w - c6 0 1",
                                 # Black en-passant capture.
                                 "8/2ppppp1/8/8/1pP3P1/8/1P1PPP2/8 b - c3 0 1",
                                 # No legal moves.
                                 "8/8/8/3p4/3P4/8/8/8 w - - 0 2",
                             ])
    def test_legal_moves(self, fen):
        # Construct a board and a corresponding python-chess Board and check that they are identical.
        board = c.CompactPawnBoard(fen)
        b = board.to_chess_board()
        move_coordinates = set([(m[0], m[1]) for m in board.legal_moves()])
        assert board.has_legal_moves() == (b.legal_moves.count() != 0)
        assert move_coordinates == set([(m.from_square - 8, m.to_square - 8) for m in b.legal_moves])
        assert board._has_legal_captures() == any(b.generate_legal_captures())
