#!/usr/bin/env python
"""Example: let the table base play Stockfish in the pawn game and verify that the table base is better."""

import chess
import pawn.pawn_game_solver as pgs
#import pawn.delegating_pawn_board as dpb
import pawn.board._compact_pawn_board as c
import chess.engine
import pickle


def generate_moves_except_kings(board):
    return (move for move in board.generate_legal_moves() if move.from_square != chess.H1 and move.from_square != chess.H8)


if __name__ == "__main__":
    # A special stockfish executable that I compiled with king moves disabled in its move generation source code.
    engine = chess.engine.SimpleEngine.popen_uci("/Users/olivne/oren/Stockfish/src/stockfish-noking")

    num_pawns = 5
    table_side = chess.BLACK

    # Load table base.
    with open('/Users/olivne/oren/{}pawns_full.pkl'.format(num_pawns), 'rb') as f:
        table = pickle.load(f)

    board = chess.Board(pgs.add_kings_to_fen(pgs.pawn_game_fen(num_pawns)))
    # board.push_san("e2e3")
    # board.push_san("e7e6")
    # print(board)

    while any(generate_moves_except_kings(board)):
        if board.turn != table_side:
            result = engine.play(board, chess.engine.Limit(time=0.2))
            move = result.move
            print("Engine: ", move)
        else:
            board_copy = chess.Board(board.fen())
            board_copy.remove_piece_at(chess.H1)
            board_copy.remove_piece_at(chess.H8)
            b = c.CompactPawnBoard(board_copy.fen())
            try:
                result = table[b.key()]
            except KeyError:
                break
            if not result[1]:
                if (board_copy.turn == chess.WHITE and result[0] > 0) or \
                        (board_copy.turn == chess.BLACK and result[0] < 0):
                    result_str = "1-0"
                elif (board_copy.turn == chess.BLACK and result[0] > 0) or \
                        (board_copy.turn == chess.WHITE and result[0] < 0):
                    result_str = "0-1"
                else:
                    result_str = "1/2-1/2"
                print("Final result:", result_str)
                break
            move = b.to_uci(result[1])
            print("Table : ", move, "result", result[0])
            move = chess.Move.from_uci(move)
        board.push(move)
    print(board)

    engine.quit()

    # Test: see that stockfish sends back score.
    # engine = chess.engine.SimpleEngine.popen_uci("/Users/olivne/oren/Stockfish/src/stockfish")
    #
    # board = chess.Board()
    # info = engine.analyse(board, chess.engine.Limit(time=2))
    # print("Score:", info["score"])
    # # Score: +20
