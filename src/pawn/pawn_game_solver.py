#!/usr/bin/env python
"""Pawn game solver. Uses alpha-beta search + pruning to infinite depth."""
from __future__ import annotations  # lazy annotations: `print_tree`'s hint referenced a non-existent type
import chess
import chess.pgn
import datetime
import logging
import pawn.board
import pickle
import time
from typing import Tuple, List

"""Unit space to print, times depth, when printing the tree (in debugging)."""
_SPACE = "  "

"""Alpha-beta pruning memo flag values."""
# TODO(oren): replace by 2 bits in memo dictionary to save space.
EXACT, LOWER_BOUND, UPPER_BOUND = range(3)


class PawnGameSolver:
    """Pawn game solver. Uses alpha-beta search with infinite depth."""
    def __init__(self, max_depth: int = -1,
                 max_depth_print: int = 0,
                 # Improves performance by 2x. But currently broken. Reinstate - need a board method for that.
                 # flip_lr: bool = False,
                 alpha_beta_pruning: bool = True,
                 board_type: str = "python-chess"):
        self.max_depth = max_depth
        self.max_depth_print = max_depth_print
        self.memo = {}
        self._start_time = None
        # self.flip_lr = flip_lr
        self.alpha_beta_pruning = alpha_beta_pruning
        self._board_type = board_type

    def principal_variation(self, fen: str, add_kings: bool = True) -> Tuple[chess.pgn.Game, List[chess.Move]]:
        """Reconstructs the principal variation (perfect play vs. perfect play) after search() has completed.
        Walks the search tree along the nodes that attain the best score at each depth."""
        board = pawn.board.create_board(self._board_type, fen)
        print(type(board))
        move, score, first_move = None, -9999, True
        while first_move or move:
            value = self.memo[board.key()]
            move_uci = value[1]
            if first_move:
                score = value[0]
                first_move = False
            if move_uci is None:
                break
            move = board.from_encoded(move_uci)
            board.push(move)
        pv = board.move_stack()

        # Add kings so that board can be loaded into clients accepting legal chess positions only.
        if add_kings:
            fen = add_kings_to_fen(fen)
        game = chess.pgn.Game()
        game.headers["Event"] = "Pawn Game"
        game.headers["Site"] = "Computer Generated"
        game.headers["Date"] = str(datetime.datetime.now().date())
        game.headers["White"] = "Perfect Play"
        game.headers["Black"] = "Perfect Play"
        game.headers["Result"] = "1-0" if score > 0 else "0-1" if score < 0 else "1/2-1/2"
        game.headers["FEN"] = fen
        game.add_line(pv)
        return game, pv

    def search(self, fen: str):
        """search_left_half - search only up to the middle of the board at depth 0. Currently broken."""
        self._start_time = time.time()
        # TODO(oren): do not allocate a new object. Reuse the the same object (unless we are searching branches in
        # parallel).
        board = pawn.board.create_board(self._board_type, fen)
        result = self._search(board, 0, -1, 1)
        #print("Key optimizations: LR {}, shift {}".format(self.flip_lr, self.shift_lr))
        return result[0], board.to_uci(result[1])

    def _search(self, board: chess.Board, depth: int, alpha: int, beta: int): # retval may be -> Tuple[Board] or -> Tuple[Board, str] at this point:
        # Searches for position in cache. If not, calls _do_search().
        # TODO(orelivne):  make board, alpha, beta members so that we can wrap the search(key) method with @lru_cache
        # annotation, and it's not found, then look in disk cache.
        key = board.key()
        best_score, best_move, flag = self._lookup_in_memo(key, depth)
        if best_score is not None:
            if self.alpha_beta_pruning:
                if flag == EXACT:
                    return best_score, best_move
                elif flag == LOWER_BOUND:
                    alpha = max(alpha, best_score)
                elif flag == UPPER_BOUND:
                    beta = min(beta, best_score)
                if alpha >= beta:
                    return best_score, best_move
            else:
                # No pruning, just return the memoized score.
                return best_score, best_move

        # Not in cache.
        alpha_original = alpha
        if depth <= self.max_depth_print:
            move_stack = board.move_stack()
            print("{}({}) {} search {} {} [{}, {}]".format(
                _SPACE * depth, depth, board.to_uci(move_stack[-1]) if move_stack else '-', key, board.fen(),
                alpha, beta))
        #            print(board)
        # Evaluate node first; if it's a leaf node, don't search the tree.
        best_score, best_move = self._evaluate(board, depth)
        # print(board)
        # print("Eval", best_score, best_move)
        if best_score is None:
            # Non-leaf node, search the tree.
            if depth == self.max_depth:
                raise Exception("Game tree depth exceeded max depth.")
            best_score = -9999
            # if any(map(lambda x: x[0] < 0 or x[1] < 0, a)):
            #     aaa=0
            #     b = list(board.legal_moves())
            for move in board.legal_moves():
                # if depth == 0:
                #     a = 9
                # if depth <= self.max_depth_print:
                #     print("{} Considering {}".format(space * (depth + 1), move))
                board.push(move)
                score = -self._search(board, depth + 1, -beta, -alpha)[0]
                board.pop()
                if score > best_score:
                    best_score = score
                    best_move = move
                if self.alpha_beta_pruning:
                    alpha = max(alpha, best_score)
                    if alpha >= beta:
                        break
                # if depth <= self.max_depth_print:
                # print("{} Current: {} best_score {} score {} depth {} #positions {} alpha {} beta {}".format(space * depth, key, best_score, score, depth, sum(self.num_positions), alpha, beta))
            if depth <= self.max_depth_print:
                move_stack = board.move_stack()
                print("{}({}) {} score {} best_move {} {} {} #positions {} positions/s {:.1f}s alpha {} beta {}".format(
                    _SPACE * depth, depth, board.to_uci(move_stack[-1]) if move_stack else '-',
                    best_score, board.to_uci(best_move), key, board.fen(), len(self.memo), len(self.memo) / (time.time() - self._start_time), alpha,
                    beta))

        best_move_encoded = board.encode_move(best_move)
        self._store_in_memo(key, best_score, best_move_encoded, alpha_original, beta)
        return best_score, best_move_encoded

    def _store_in_memo(self, key, score, best_move, alpha_original, beta):
        if score <= alpha_original:
            flag = UPPER_BOUND
        elif score >= beta:
            flag = LOWER_BOUND
        else:
            flag = EXACT
        self.memo[key] = (score, best_move, flag)

    def _lookup_in_memo(self, key: str, depth: int) -> Tuple[int, int, int]:
        try:
            # if depth <= self.max_depth_print:
            #     print("{}Cached: {} {}".format(_SPACE * depth, key, self.memo[key]))
            #     pass
            return self.memo[key]
        except KeyError:
            pass

        # Add L-R, shift symmetries here.

        # Not in memo.
        return None, None, None

    def _evaluate(self, board, depth):
        score = board.evaluate()
        if score is not None:
            if depth <= self.max_depth_print:
                key = board.key()
                print("{}Leaf: board {} score {}".format(_SPACE * depth, key, score))
            return score, None
        if not board.has_legal_moves():
            # This side has pawns but there are no legal moves == stalemate (draw).
            if depth <= self.max_depth_print:
                key = board.key()
                print("{}{} stalemate depth {} #positions {} positions/s {:.2f}s".format(_SPACE * depth, key, depth, len(self.memo), len(self.memo) / (time.time() - self._start_time)))
            return 0, None
        # Inconclusive result.
        return None, None


def solve_pawn_game(num_pawns: int, board_type: str = "python-chess") -> Tuple[List[int], PawnGameSolver]:
    game_solver = PawnGameSolver(max_depth_print=2, board_type=board_type)
    game_result = [None] * (num_pawns + 1)
    for n in range(1, num_pawns + 1):
        print("Solving with {} pawns".format(n))
        board = chess.Board(pawn_game_fen(n))
        #board.push_san('d2d4')
        game_result[n] = game_solver.search(board.fen())
        print("result with {} pawns: {} #positions {}".format(n, game_result[n], len(game_solver.memo)))
        checkpoint = '../{}pawns_full.pkl'.format(n)
        print("Saving to {}".format(checkpoint))
        with open(checkpoint, 'wb') as ff:
            pickle.dump(game_solver.memo, ff)
    return game_result, game_solver


def pawn_game_fen(num_pawns):
    def optional_str(s): return str(s) if s else ""
    left_space = (8 - num_pawns) // 2
    right_space = 8 - num_pawns - left_space
    def pawn_row(pawn_symbol): return optional_str(left_space) + pawn_symbol * num_pawns + optional_str(right_space)
    return "/".join(["8", pawn_row("p")] + ["8"] * 4 + [pawn_row("P"), "8"]) + " w - - 0 1"


PAWN_GAME_FEN_1P = pawn_game_fen(1)
PAWN_GAME_FEN_2P = pawn_game_fen(2)
PAWN_GAME_FEN_3P = pawn_game_fen(3)
PAWN_GAME_FEN_4P = pawn_game_fen(4)
PAWN_GAME_FEN_5P = pawn_game_fen(5)
PAWN_GAME_FEN_6P = pawn_game_fen(6)
PAWN_GAME_FEN_7P = pawn_game_fen(7)
PAWN_GAME_FEN_8P = pawn_game_fen(8)



def print_tree(board: pawn.board.Board, memo, depth: int = 0):
    """
    Prints the game solution sub-tree rooted at a particular position stored in a memo data structure.
    :param board: position of root node of tree in `memo`.
    :param memo: game solution memo dat astructure.
    :param depth: print up to this depth.
    """
    #print('depth', depth, '\n', board)
    space = ' '
    key = board.key()
    value = memo[key]
    print("{} ({}) {} {} best child {} legal moves {}".format(
        space * depth, depth, board.to_uci(board.move_stack[-1]) if board.move_stack else '-', value[0], value[1],
        list(map(board.uci, board.legal_moves))))
    if not value[1]:
        print("{} done".format(space * depth))
        return
    for move in board.legal_moves:
        board.push(move)
        print_tree(board, memo, depth + 1)
        board.pop()
    print("{} done".format(space * depth))


def add_kings_to_fen(fen):
    """Adds kings on h1 and h8 to a FEN string and outputs the updated string."""
    board = chess.Board(fen)
    board.set_piece_at(chess.H1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
    return board.fen()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
    #solver = PawnGameSolver()
    #fen = '8/2pppp2/8/8/8/2P5/3PPP2/8 b - - 0 1'
    #board = chess.Board(pawn_game_fen(4))

    # f = PawnGameSolver(max_depth_print=1000, board_type="python-chess")
    # f.search(PAWN_GAME_FEN_2P)

    game_result, game_solver = solve_pawn_game(4)#, board_type="compact")
    game, pv = game_solver.principal_variation(pawn_game_fen(4))
    print(game)
#f = PawnGameSolver(max_depth_print=2, alpha_beta_pruning=False)
#    p = PawnGameSolver(max_depth_print=-1, alpha_beta_pruning=True)
#    result = p.search(board.fen())
#    print(result)
    # result = solver.search(PAWN_GAME_FEN_8P)
    #solver = PawnGameSolver(max_depth_print=3)
    #result = solver.search(PAWN_GAME_FEN_3P)
    #result, solver = solve_pawn_game(4)
    #import pickle
    #with open("/Users/olivne/memo.pkl", "wb") as f:
    #    pickle.dump(solver.memo, f)
    #print(result)
