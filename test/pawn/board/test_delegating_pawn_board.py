"""Pawn game solver unit tests."""
import chess
import pawn.board._delegating_pawn_board as pgs


class TestDelegatingPawnBoard:
    def test_pawn_race_captures_is_inconclusive(self):
        # White's pawn is more advanced. It can be captured, but
        # . . . . . . . .
        # . . . . . . . .
        # . . p . p . . .
        # . . . P . p . .
        # . . P . P . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        board = chess.Board("8/8/2p1p3/3P1p2/2P1P3/8/8/8 b - - 0 7")
        evaluator = pgs._Evaluator(board)

        # White does not have a clear passer. True, he can capture a pawn, it's not his move.
        assert evaluator.min_steps_to_promotion(chess.WHITE) == 0
        # Black has a passer if he captures, but we are not considering captures, so a passer does not exist for us.
        assert evaluator.min_steps_to_promotion(chess.BLACK) == 0
        # The evaluation is inconclusive.
        assert evaluator.evaluate() is None

    def test_white_has_passer_upon_capture_and_blacks_can_be_captured(self):
        # White has a passed pawn if it's his turn since he can capture on a6 or b5.
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . p . . . . .
        # . . . P . . . .
        # . . . . . . . .
        board = chess.Board("8/8/8/8/8/2p5/3P4/8 w - - 0 1")
        evaluator = pgs._Evaluator(board)

        assert evaluator.min_steps_to_promotion(chess.WHITE) == 0
        assert evaluator.min_steps_to_promotion(chess.BLACK) == 0
        assert evaluator.evaluate() is None

    def test_white_has_passer_upon_capture(self):
        # White has a passed pawn if it's his turn since he can capture on a6 or b5.
        # . . . . . . . .
        # . . . . . . . .
        # p . p . . . . .
        # p P . . . . . .
        # . . P . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        board = chess.Board("8/8/p1p5/pP6/2P5/8/8/8 w - - 0 1")
        evaluator = pgs._Evaluator(board)

        assert evaluator.min_steps_to_promotion(chess.WHITE) == 0
        assert evaluator.min_steps_to_promotion(chess.BLACK) == 4
        assert evaluator.evaluate() is None

    def test_black_has_passer_upon_capture_but_doesnt_count(self):
        # Black has a passed pawn if it's his turn since he can capture on a4. But we saw that dealing with captures
        # is too hard so falling back to no passers and inconclusive outcome.
        # . . . . . . . .
        # p . . . . . . .
        # . . . . . . . .
        # . p . . . . . .
        # P P . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        board = chess.Board("8/1p6/8/p7/PP6/8/8/8 b")
        evaluator = pgs._Evaluator(board)

        assert evaluator.min_steps_to_promotion(chess.WHITE) == 0
        assert evaluator.min_steps_to_promotion(chess.BLACK) == 0
        assert evaluator.evaluate() is None

    def test_most_advanced_passer_rank_has_capture_but_not_his_turn(self):
        # White would have a passed pawn if it's his turn since he can capture on a6 or b5, but since it's Black"s turn
        # he doesn"t.
        # . . . . . . . .
        # . . . . . . . .
        # p . p . . . . .
        # p P . . . . . .
        # . . P . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        board = chess.Board("8/8/p1p5/pP6/2P5/8/8/8 b - - 0 1")
        evaluator = pgs._Evaluator(board)

        assert evaluator.min_steps_to_promotion(chess.WHITE) == 0
        assert evaluator.min_steps_to_promotion(chess.BLACK) == 4

    def test_most_advanced_passer_rank_no_capture(self):
        # Black potentially has a passed pawn but it's not his turn and he doesn"t have a capture.
        # . . . . . . . .
        # p . . . . . . .
        # . . . . . . . .
        # . p . . . . . .
        # P P . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        board = chess.Board("8/p7/8/1p6/PP6/8/8/8 w")
        evaluator = pgs._Evaluator(board)

        assert evaluator.min_steps_to_promotion(chess.WHITE) == 0
        assert evaluator.min_steps_to_promotion(chess.BLACK) == 0

    def test_enpassant_inconclusive_result(self):
        # White has an enpassant dxc6, and thus an advanced pawn, but it's a capture, so no conclusion.
        # . . . . . . . .
        # . . . . . . . .
        # . . . p . p . .
        # . . p P . . . .
        # . . . . P . . .
        # . . . . . . . .
        # . . . . . P . .
        # . . . . . . . .
        board = chess.Board("8/8/3p1p2/2pP4/4P3/8/5P2/8 w - c6 0 6")
        evaluator = pgs._Evaluator(board)

        assert evaluator.evaluate() is None

    def test_unblocked_pawn_on_the_6th_rank_is_win(self):
        # . . . . . . . .
        # . . . . . . . .
        # . . . P . . . .
        # . . . . P p . .
        # . . p P . . . .
        # . P p . . . . .
        # . . . . . . . .
        # . . . . . . . .
        board = chess.Board('8/8/3P4/4Pp2/2pP4/1Pp5/8/8 w - - 0 13')
        evaluator = pgs._Evaluator(board)

        assert evaluator.evaluate() == 1
