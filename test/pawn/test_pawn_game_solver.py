"""Pawn game solver unit tests."""
import pawn.pawn_game_solver as pgs
import pytest
import unittest


class TestPawnGameSolver: #(unittest.TestCase):
    @staticmethod
    def create_solver():
        return pgs.PawnGameSolver(max_depth_print=100)

    def test_solver_equal_rank_passers_side_to_move_wins(self):
        # Same number of squares away, White wins.
        # . . . . . . . .
        # p . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . P . . . . .
        # . . . . . . . .
        solver = TestPawnGameSolver.create_solver()
        assert solver.search("8/p7/8/8/8/8/2P5/8 w - - 0 1")[0] == 1

    def test_solver_black_rank_passer_closer_black_wins(self):
        # Same number of squares away, White wins.
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # p . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . P . . . . .
        # . . . . . . . .
        solver = TestPawnGameSolver.create_solver()
        assert solver.search("8/8/8/p7/8/8/2P5/8 w - - 0 1")[0] == -1

    def test_neighboring_pawns_is_zugzwang(self):
        # Neighboring pawns, Zugzwang.
        # . . . . . . . .
        # p . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . P . . . . . .
        # . . . . . . . .
        solver = TestPawnGameSolver.create_solver()
        assert solver.search("8/p7/8/8/8/8/1P6/8 w - - 0 1")[0] == -1

    def test_opposing_pawns_is_draw(self):
        # Opposing pawns, draw.
        # . . . . . . . .
        # p . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # P . . . . . . .
        # . . . . . . . .
        solver = TestPawnGameSolver.create_solver()
        assert solver.search(pgs.PAWN_GAME_FEN_1P)[0] == 0

    def test_two_pawns_is_zugzwang(self):
        # Two pawns each, apparently Zugzwang.
        # . . . . . . . .
        # p p . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # P P . . . . . .
        # . . . . . . . .
        solver = TestPawnGameSolver.create_solver()
        assert solver.search(pgs.PAWN_GAME_FEN_2P)[0] == -1
#        print(solver.principal_variation("8/pp6/8/8/8/8/PP6/8 w - - 0 1"))

    def test_three_pawns_is_draw(self):
        # Two pawns each, apparently Zugzwang.
        # . . . . . . . .
        # p p p . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # . . . . . . . .
        # P P P . . . . .
        # . . . . . . . .
        solver = TestPawnGameSolver.create_solver()
        assert solver.search(pgs.PAWN_GAME_FEN_3P)[0] == 0

    def test_enpassant(self):
        # White can do an enpassant an win.
        # . . . . . . . .
        # . . . . . . . .
        # . . . p . p . .
        # . . p P . . . .
        # . . . . P . . .
        # . . . . . . . .
        # . . . . . P . .
        # . . . . . . . .
        solver = TestPawnGameSolver.create_solver()
        assert solver.search('8/8/3p1p2/2pP4/4P3/8/5P2/8 w - c6 0 6')[0] == 1

    @unittest.skip("Flip LR currently broken.")
    def test_flip_lr_caching_doesnt_change_result(self):
        data = [
            ("8/3ppp2/8/2p5/5P2/8/2PPP3/8", 1),
            ("8/2pp1p2/4p3/8/4P3/8/2PP1P2/8", 1),
            ("8/2pp1p2/4p3/8/2P5/4P3/3P1P2/8", 0),
        ]
        for fen, score in data:
            solver = pgs.PawnGameSolver(flip_lr=True, max_depth_print=-1)
            result = solver.search(fen)[0]
            solver = pgs.PawnGameSolver(max_depth_print=-1)
            result_lr = solver.search(fen)[0]
            assert result_lr == result

    @pytest.mark.parametrize("num_pawns", list(range(1, 3)))
    def test_alpha_beta_pruning_doesnt_change_result(self, num_pawns):
        fen = pgs.pawn_game_fen(num_pawns)
        solver = pgs.PawnGameSolver(alpha_beta_pruning=False, max_depth_print=-1)
        result = solver.search(fen)[0]
        solver = pgs.PawnGameSolver(max_depth_print=-1)
        result_pruned = solver.search(fen)[0]
        assert result_pruned == result

    def test_principal_variation(self):
        fen = pgs.pawn_game_fen(2)
        solver = pgs.PawnGameSolver(max_depth_print=-1, board_type="compact")
        result = solver.search(fen)[0]
        expected = """[FEN "7k/3pp3/8/8/8/8/3PP3/7K w - - 0 1"]

1. e3 e6 2. e4 e5 3. d3 d6 4. d4 exd4 0-1"""
        actual, pv = solver.principal_variation(fen)
        assert expected in str(actual)

    @pytest.mark.parametrize("num_pawns,expected_result",
                             list(enumerate([(0, 'd2d3'), (-1, 'e2e3'), (0, 'e2e3'), (1, 'e2e4')], 1)))
    def test_solving_small_pawn_number_yields_correct_result(self, num_pawns, expected_result):
        solver = pgs.PawnGameSolver(max_depth_print=-1)
        game_result = solver.search(pgs.pawn_game_fen(num_pawns))
        assert game_result == expected_result

    @pytest.mark.parametrize("fen",
                             [
                                 '8/1p6/3p4/1p6/4pP2/2P1P3/8/8 b - f3 0 1',
                                 pgs.pawn_game_fen(1),
                                 pgs.pawn_game_fen(2),
                                 pgs.pawn_game_fen(3),
                             ])
    def test_solve_with_compact_board_same_as_chess_board(self, fen):
        solver = pgs.PawnGameSolver(max_depth_print=-1)
        slow_result = solver.search(fen)
        solver_fast = pgs.PawnGameSolver(max_depth_print=2, board_type="compact")
        fast_result = solver_fast.search(fen)
        assert slow_result[0] == fast_result[0]


def wip_test_pruning(board):
    # Pruning debugging: walk down the tree and find when negamax + pruning still differs from pure negamax till
    # we get a simpler problem to understand.
    depth = 0
    max_depth = 10
    while depth <= max_depth:
        print("depth {}".format(depth))
        print(board.fen())
        print(board)
        results_vs_pruning = {}
        for alpha_beta_pruning in (True, False):
            print("Pruning {}".format(alpha_beta_pruning))
            solver = pgs.PawnGameSolver(max_depth_print=100, alpha_beta_pruning=alpha_beta_pruning)
            results = []
            for move in board.legal_moves:
                board.push(move)
                result = solver.search(board.fen())
                print(move, result)
                board.pop()
                results.append((move, result))
            print("root", solver.search(board.fen()))
            results_vs_pruning[alpha_beta_pruning] = results
        try:
            diff = next(
                (x, y) for x, y in zip(results_vs_pruning[True], results_vs_pruning[False]) if x[1][0] != y[1][0])
            print("Different", diff)
            board.push(diff[0][0])
        except StopIteration:
            print("No different between pruning, no pruning")
            break
