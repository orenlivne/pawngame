♟️ I solved the pawn game — chess played with pawns only, no kings — exactly, for up to 8 pawns per side.

It's a well-known teaching position (two pawn phalanxes racing to promote), but its game-theoretic value hadn't been settled in print beyond the smallest cases. The 8-pawn game in particular had circulated as an open question in informal play.

Result: it's a first-player (White) win, under both the game's stated rule (no legal move = loss) and the chess-stalemate rule (no legal move = draw). En passant turns out to be essential, not incidental — removing it flips 4 of the 16 solved values. I also solved a third variant where a player may pass (but not twice running): every game there is governed entirely by zugzwang.

The solver combines a proved passed-pawn "race" evaluator, the game's symmetry group, a lock-free parallel search, and a packed transposition table — cross-validated against an independent reference implementation, unpruned search, and hundreds of games against Stockfish per case.

Paper: https://github.com/orenlivne/pawngame/blob/main/submission/pawngame_sage.pdf
Code, tests, and all result data: https://github.com/orenlivne/pawngame

Submitted to the ICGA Journal. Not on arXiv — endorsement requirements there have gotten steep enough that I'm going straight to peer review instead.

#chess #combinatorialgametheory #computerscience #gamesolving
