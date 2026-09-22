# ICGA Journal — submission metadata

The *ICGA Journal* is published by SAGE and submitted through ScholarOne /
Manuscript Central (https://mc.manuscriptcentral.com/icga, linked from
https://journals.sagepub.com/home/icg). Peer review is **single-blind** by default
(double-blind on request). SAGE accepts **free-format initial submissions** — the
generic PDF is acceptable at first submission; the `sagej` SAGE LaTeX class is
required at revision/acceptance. Both versions are provided in this folder (see
"Files" below). Fill the bracketed placeholders before uploading.

---

## Article
- **Title:** Exact Solution of the Pawn Game for up to Eight Pawns per Side
- **Running head:** Livne
- **Article type:** Original (research) article
- **Word count (body, approx.):** 4,300
- **Figures:** 4 (fig:start starting position; fig:race race evaluator; fig:grid
  critical-position grid; fig:break the winning asymmetry)
- **Tables:** 4 (tab:stockfish tablebase-vs-Stockfish; tab:results game values +
  openings; tab:scale solve sizes/times; tab:noep values with/without en passant)
- **References:** 5

## Abstract
The pawn game is chess played with pawns only: each side starts with n pawns on its
second rank, pawns move and capture as in chess (including the initial double step
and en passant), and a player wins by advancing a pawn to the far rank, by capturing
every enemy pawn, or by leaving the opponent with no legal move. We solve the game
exactly for n = 1..8 pawns per side (left-justified for n < 8) under two rulesets
that differ only in the treatment of a player with no legal move: a loss (the game's
stated rule) or a draw (chess stalemate). Under the loss rule the game is finite and
drawless, and the full eight-pawn game is a first-player win; White wins for every
n >= 6 and for n = 4, while Black wins for n = 1,2,3,5. We give the outcomes under
both rulesets, the optimal opening moves, and the winning technique. En passant
proves essential rather than incidental: removing it flips four of the sixteen
values — every White win under the chess-stalemate rule (n = 4,6,8) and the
seven-pawn game under the game's rule. The solver combines a bitboard search with a
proved passed-pawn evaluator that settles many positions without expanding them,
board symmetries, a packed transposition table, and a lock-free parallel search;
correctness rests on fuzzing move generation against an independent engine and
cross-validating every shortcut against unpruned search, and is further stress-tested
by a play-test in which the tablebase never loses to Stockfish from a non-losing
side. A section aimed at chess players interprets the solution.

## Keywords
pawn game; exact game solving; combinatorial game theory; passed-pawn race;
en passant; alpha–beta search; transposition table; chess endgames

## Authors
1. **Oren Livne** (corresponding author; sole author)
   - Email: oren.livne@gmail.com
   - Affiliation: [to be completed]
   - Postal address: [to be completed]
   - ORCID: [to be completed — register free at https://orcid.org if none]

## Declarations
- **Declaration of conflicting interests:** The author declares no potential
  conflicts of interest with respect to the research, authorship, and/or publication
  of this article.
- **Funding:** The author received no financial support for the research,
  authorship, and/or publication of this article.
- **Data availability:** The solver, the independent reference oracle, all raw solve
  and play-test result files, and the manuscript source are openly available at
  https://github.com/orenlivne/pawngame .
- **Ethics / human or animal participants:** Not applicable.
- **Author contributions:** Sole author; conceived, implemented, analysed, and wrote.
- **Prior dissemination / preprint:** [none — or add arXiv id if you post one].

## Suggested reviewers (optional)
- [Optional: 2–3 names + emails of researchers in game-solving / combinatorial game
  theory, none co-authors or close collaborators. Leave blank if unsure.]

## Files in this submission folder
- `pawngame_sage.tex` — manuscript in the SAGE `sagej` house style (compiles to an
  8-page two-column PDF with `pdflatex`; needs `sagej.cls` + a `.bst`, both included).
- `sagej.cls`, `SageV.bst`, `SageH.bst` — the SAGE class and reference styles.
- `../paper/pawngame.tex` — the same manuscript in a plain one-column `article`
  layout (valid for SAGE free-format initial submission).
- `cover_letter.md` — cover letter (convert to PDF/DOCX as the portal requires).
- Result artifacts: `../gcp/results/results.txt` (32 solves), `stockfish_playtest.txt`
  (15 play-test tallies), referenced for reproducibility.

## Notes before uploading
- Confirm the reference style ICGA currently mandates (SAGE offers Harvard/Vancouver/
  APA); this version uses numbered (Vancouver, `sagev`). Switch the class option to
  `sageh` (Harvard) if the guidelines require author–year.
- ScholarOne wants a single manuscript file with figures/tables embedded (both
  provided PDFs already embed everything).
