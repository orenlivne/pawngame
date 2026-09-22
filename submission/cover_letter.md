# Cover letter — ICGA Journal submission

Oren Livne
oren.livne@gmail.com
[Affiliation and postal address — to be completed]

22 September 2026

Dear Editor-in-Chief,

Please consider the enclosed manuscript, **"Exact Solution of the Pawn Game for
up to Eight Pawns per Side,"** for publication in the *ICGA Journal* as an original
research article.

The pawn game — chess played with pawns only, no kings — is a familiar teaching
position, but its game-theoretic value has not, to our knowledge, been settled in
print beyond the smallest cases. This paper solves it exactly for all $n = 1,\dots,8$
pawns per side (left-justified for $n<8$) under both the game's stated rule
(no legal move = loss) and the chess-stalemate variant (no legal move = draw),
settling the previously open eight-pawn game: it is a first-player (White) win under
both rulesets.

We believe the work fits the ICGA Journal's scope and will interest its readership
for three reasons:

1. **A completed game solution with a proved core.** Beyond the tabulated values and
   optimal openings, the solver rests on a passed-pawn "race" evaluator whose every
   verdict is a theorem (an exact result under the loss rule, and a two-sided bound
   that drives alpha–beta cutoffs under the draw rule), together with the game's
   symmetry group and a lock-free parallel transposition table.

2. **A clean, testable finding of independent interest:** en passant is *essential*,
   not incidental. Re-solving with en passant disabled flips four of the sixteen
   values — every White win under the draw rule ($n = 4, 6, 8$) and the seven-pawn
   game under the loss rule.

3. **A section written for chess players**, connecting the solution to over-the-board
   themes (the outside passer won by a tempo, the breakthrough sacrifice), in the
   spirit of Philidor's maxim that the pawns are the soul of chess.

Correctness is established by fuzzing the move generator against an independent
engine and by cross-validating every search shortcut against unpruned search;
as an additional stress test, the tablebase never loses to Stockfish from a
non-losing side across 100 games per case. The solver, its independent reference
oracle, all result files, and the manuscript source are openly available in the
accompanying repository (https://github.com/orenlivne/pawngame), so every number in
the paper is reproducible.

The manuscript is original, has not been published previously, and is not under
consideration elsewhere. It has a single author. There are no conflicts of interest
and no funding to declare. We have no objection to single-blind review (the standard
for the journal) and can prepare an anonymized version should double-blind review be
preferred.

Thank you for your consideration.

Sincerely,

Oren Livne
oren.livne@gmail.com
