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
- **Word count (body, approx.):** 5,200 (includes the pass-variant section)
- **Figures:** 4 (fig:start starting position; fig:race race evaluator; fig:grid
  critical-position grid; fig:break the winning asymmetry)
- **Tables:** 4 (tab:stockfish tablebase-vs-Stockfish; tab:results game values +
  openings; tab:scale solve sizes/times; tab:noep values with/without en passant)
- **References:** 7
- **Note:** the manuscript also includes a third rule variant (Section "A third
  rule: passing") added after the initial draft; the pass variant is solved exactly
  for the stated rule (n=1..8, all White wins) and chess stalemate (n=1..7, all
  draws), with the n=8 draw recorded as a conjecture (its table exceeds the machine).

## Abstract
The pawn game is chess played with pawns only: each side starts with n pawns on its
second rank, pawns move and capture as in chess (including the initial double step
and en passant), and a player wins by advancing a pawn to the far rank, by capturing
every enemy pawn, or by leaving the opponent with no legal move. We solve the game
exactly for n = 1..8 pawns per side (left-justified for n < 8) under two rulesets
that differ only in the treatment of a player with no legal move: a loss (the game's
stated rule) or a draw (chess stalemate). Under the loss rule the game is finite and
drawless, and the full eight-pawn game is a first-player win; White wins for
n = 6,7,8 and for n = 4, while Black wins for n = 1,2,3,5. We give the outcomes under
both rulesets, the optimal opening moves, and the winning technique. En passant
proves essential rather than incidental: removing it flips four of the sixteen
values — every White win under the chess-stalemate rule (n = 4,6,8) and the
seven-pawn game under the game's rule. The solver combines a bitboard search with a
proved passed-pawn evaluator that settles many positions without expanding them,
board symmetries, a packed transposition table, and a lock-free parallel search;
correctness rests on fuzzing move generation against an independent engine and
cross-validating every shortcut against unpruned search, and is further stress-tested
by a play-test in which the tablebase never loses to Stockfish from a non-losing
side. We also solve a variant in which a player may pass, but not twice running:
there the game is a first-player win under the stated rule (n <= 8) and a draw under
chess stalemate (verified for n <= 7, conjectured beyond), showing the outcomes to be
governed by zugzwang. A section aimed at chess players interprets the solution.

(Authoritative abstract text: copy from the compiled `pawngame_sage.pdf`, which is
kept in sync with `pawngame_sage.tex`.)

## Keywords
pawn game; exact game solving; combinatorial game theory; passed-pawn race;
en passant; alpha–beta search; transposition table; chess endgames

## Authors
1. **Oren Livne** (corresponding author; sole author)
   - Email: oren.livne@gmail.com
   - Affiliation: Pine Birch Analytics, LLC
   - Postal address: 35 Kelinger Rd, Churchville, PA 18966-1033, USA
   - ORCID: 0000-0001-6700-483X

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
- `pawngame_sage.tex` — **the authoritative manuscript**, in the SAGE `sagej` house
  style (compiles to a 10-page PDF with `pdflatex`; needs `sagej.cls`, included). The
  bibliography is inline (`thebibliography`), so no `.bib`/BibTeX run is needed.
- `pawngame_sage.pdf` — the compiled manuscript; this single PDF is what to upload
  for a free-format initial submission (figures and tables are embedded).
- `sagej.cls`, `SageV.bst`, `SageH.bst` — the SAGE class and reference styles.
- `cover_letter.md` — cover letter (convert to PDF/DOCX as the portal requires).
- Result artifacts under `../gcp/results/`: `results.txt` and `pass_results.txt`
  (solve values/sizes/times), `stockfish_playtest.txt` / `pass_sf_local.txt`
  (play-test tallies), referenced for reproducibility.
- **Do not use** the older `../paper/pawngame.tex` plain-layout draft: it predates
  the pass variant and the revised chess section and is out of date.

## Notes before uploading
- Confirm the reference style ICGA currently mandates (SAGE offers Harvard/Vancouver/
  APA); this version uses numbered (Vancouver, `sagev`). Switch the class option to
  `sageh` (Harvard) if the guidelines require author–year.
- ScholarOne wants a single manuscript file with figures/tables embedded (both
  provided PDFs already embed everything).
