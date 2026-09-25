# ICGA Journal — submission metadata

The *ICGA Journal* is published by SAGE and submitted through ScholarOne /
Manuscript Central (https://mc.manuscriptcentral.com/icga, linked from
https://journals.sagepub.com/home/icg). Peer review identity transparency is
**single anonymized** (reviewers know the author; the author does not know
reviewers). SAGE accepts **free-format initial submissions** — the generic PDF is
acceptable at first submission; the `sagej` SAGE LaTeX class is required at
revision/acceptance. Both versions are provided in this folder (see "Files" below).

**Reference style: APA**, confirmed against both the live "Preparing your
manuscript" guidelines ("The journal follows the APA reference style") and a
2026 published ICGA Journal article's actual reference list (author-year,
`Author, A. (Year). Title. Source.`). The manuscript uses the `sagej` class's
`sageapa` option (loads `mslapa`), with each `\bibitem[Author, Year]{key}` hand-set
to render `(Author, Year)` in text — not the numbered `sagev`/Vancouver style used
in an earlier draft.

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
(183 words — under the journal's 200-word limit)

The pawn game—chess with pawns only—is solved exactly for n = 1,...,8 pawns per
side under two rulesets differing only in how a player with no legal move is
scored: a loss (the stated rule) or a draw (chess stalemate). The game is finite;
under the loss rule it is drawless, and the eight-pawn game is a first-player win,
as are n = 4,6,7, while Black wins n = 1,2,3,5. We give the outcomes, optimal
openings, and winning technique—an unstoppable outside passed pawn—under both
rulesets, and show en passant is essential: disabling it flips four of the sixteen
values. The solver combines a bitboard search with a proved passed-pawn evaluator,
board symmetries, a packed transposition table, and a lock-free parallel search,
verified against an independent engine, unpruned search, and a Stockfish play-test
the tablebase never loses. A pass variant—where a player may pass but not twice
running—is a first-player win under the stated rule (n <= 8) and a draw under chess
stalemate (n <= 7, conjectured beyond), showing outcomes governed by zugzwang.

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
  style (compiles to a 10-page PDF with `pdflatex`; needs `sagej.cls` +
  `mslapa.sty` + the 11 `diag-*.pdf` figure files, all included). The bibliography
  is inline (`thebibliography`), so no `.bib`/BibTeX run is needed.
- `pawngame_sage.pdf` — the compiled manuscript; upload this alone for a
  free-format initial submission (figures/tables embedded).
- `sagej.cls`, `mslapa.sty` — required style files (`mslapa` is what the `sageapa`
  reference-style option loads). `SageV.bst`/`SageH.bst` are not used (no BibTeX —
  the bibliography is hand-set for APA).
- `diag-*.pdf` (11 files) — the manuscript's figures/diagrams, **pre-rendered**
  from the same FEN strings with `xskak`/`chessboard` and included via
  `\includegraphics`, rather than drawn live in the document. This removes the
  `xskak`/`chessboard`/`tikz` dependency from the `.tex` entirely — see "LaTeX
  upload" note below for why.
- `cover_letter.md` — cover letter (convert to PDF/DOCX as the portal requires).
- Result artifacts under `../gcp/results/`: `results.txt` and `pass_results.txt`
  (solve values/sizes/times), `stockfish_playtest.txt` / `pass_sf_local.txt`
  (play-test tallies), referenced for reproducibility.
- **Do not use** the older `../paper/pawngame.tex` plain-layout draft: it predates
  the pass variant and the revised chess section and is out of date.

## Notes before uploading
- **LaTeX upload (ScholarOne "LaTeX Main Document" + "LaTeX Supplementary File"
  flow):** upload `pawngame_sage.tex` as the main document, and `sagej.cls`,
  `mslapa.sty`, and all 11 `diag-*.pdf` files as supplementary files. Earlier the
  `.tex` used `xskak`/`chessboard` (built on `tikz`) to draw the chess diagrams
  live; ScholarOne's compile server rejected it ("File will not display in
  proof") — their LaTeX environment is documented to lack even some common
  packages (their own FAQ cites missing `rotating.sty`/`textcase.sty`), and
  `xskak`/`chessboard` is a niche package needing its own chess-piece fonts, the
  likely single point of failure. Fixed by pre-rendering all 11 diagrams to PDF
  locally and swapping to plain `\includegraphics` — verified by compiling
  `pawngame_sage.tex` + `sagej.cls` + `mslapa.sty` + the 11 `diag-*.pdf` files
  alone, in a bare directory with nothing else on the TeX search path: compiles
  clean, all figures pixel-identical to the originals. If ScholarOne's proof
  generation still fails after this, upload `pawngame_sage.pdf` as a
  free-format submission instead (skip the LaTeX-file flow entirely) — the PDF
  route is officially supported for initial submission and sidesteps their
  compiler altogether.
- ScholarOne wants a single manuscript file with figures/tables embedded (the
  provided PDF already embeds everything).
- The `©The Author(s) 0000` placeholder in the PDF header is expected: `sagej.cls`
  leaves `\volumeyear` at its default until SAGE production sets it at acceptance;
  there is no author-facing macro to fill it in pre-acceptance.
