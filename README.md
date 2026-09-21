# Pawn Game Solver
Pawn Game Solver

## TODO
1. Further tree pruning:
  - Up-down flip - reverse colors and side to move - the evaluation is the negative of the evaluation of current the position.
  - Vertical translation (shift by x ranks up or down). Evaluation depends on passers - but sometimes can be deduced
  simply - if White is winning then it is winning when we shift the position up. Similarly Black/down.
  - Shift + LR
  - Combinations of smaller boards if there are multiple pawn islands.
2. C++/Cython implementation.
3. Parallelization of tree branches; don't share cache if it's too complex.
3. Evaluation optimization:
  - Encode board as 64-bit x 2-bits (at every square, either White, Black or blank). Could be two 64-bitmaps.
4. Test against a chess engine if possible (that does not move the kings, if available).
5. Create a book (syzygy format) so we know what the perfect game is or draw conclusions on pawn masses.
6. Generate = "computer-composed" endgame studies on an 8x10 board where the kings do not move, just pawns.
7. Write a book about the pawn game. Maybe title it "The Pawn Game".
8. Make board, alpha, beta members so that we can wrap the search(key) method with @lru_cache. If not found in cache,
   look in diskcache.
9. Encode best move as two chess squares (12 bits).


Done
====
1. Only search half of the initial moves (from left to the middle of the board). That is a special kind of LR flip -
we don't even bother searching in the other half. DROPPED - led to a bug and is a special case of LR flipping.
2. Implemented tree pruning:
  - Run smaller games first. Helps a little since cache is larger.
  - Left-right flip - same evaluation. 2x speedup.
  - Horizontal translation (shift by x files to the left or to the right). Same evaluation. Slows run, since this
    requires many key lookups.
