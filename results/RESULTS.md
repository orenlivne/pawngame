# Pawn-Game — Exact Results (perfect play)

n-vs-n pawns, **left-justified** for n < 8 (White rank 2, Black rank 7, White to
move), no kings. Solved exactly under both rulesets. See
[`src/pawn/exact/README.md`](../src/pawn/exact/README.md) for methods/verification.

Value is from **White's** perspective: **W** = White wins, **B** = Black wins, **=** = draw.

| n | loss-rule (authoritative) | draw-rule (chess stalemate) |
|---|:---:|:---:|
| 1 | **B** | = |
| 2 | **B** | **B** |
| 3 | **B** | = |
| 4 | **W** | **W** |
| 5 | **B** | = |
| 6 | **W** | **W** |
| 7 | **W** | = |
| 8 | **W** | _computing_ |

**Headline: the full 8-vs-8 pawn game is a first-player (White) win** under the
authoritative loss-rule (440.8M searched states, 71 min). Loss-rule sequence
B,B,B,W,B,W,W,W: White wins for all n ≥ 6 (and n = 4).

Under the **loss-rule the game has no draws** — every n is a forced win for one
side. The n = 4 result (White) matches the lichess/chess.com community finding for
4-vs-4; n = 5..8 appear not to have been published anywhere.

## Verified state counts (loss-rule, C++ core, color-sym + leaf-skip)

| n | value | stored (minsub=1) | time |
|---|:---:|---:|---:|
| 5 | B | 398,327 | 0.1 s |
| 6 | W | 4,961,644 | 1.5 s |
| 7 | W | 151,051,767 (35.5M at minsub=16) | ~170 s |
| 8 | ? | ~5.4×10⁸ (minsub=64) | ~1.5 h |

## Sample perfect-play lines

Left-justified, UCI (`from``to`), White's moves numbered.

**loss-rule**
```
n=1  B : 1.a2a4 a7a5                      (then White is stalemated -> loses)
n=2  B : 1.a2a4 a7a5 2.b2b4 a5b4 3.a4a5 b4b3 4.a5a6 b7a6
n=3  B : 1.a2a4 a7a5 2.b2b4 a5b4 3.a4a5 b4b3 4.c2b3 c7c5 5.a5a6 b7a6 6.b3b4 c5b4
n=4  W : 1.b2b4 a7a5 2.b4a5 b7b5 3.a5b6 c7b6 4.a2a4 b6b5 5.a4b5 d7d5 6.b5b6 d5d4 7.b6b7 d4d3 8.b7b8 (touchdown)
n=5  B : 1.a2a4 c7c5 2.a4a5 c5c4 3.a5a6 b7a6 4.b2b4 c4b3 5.c2b3 a6a5 6.d2d4 a5a4 7.b3a4 d7d5 8.a4a5 a7a6 9.e2e4 d5e4 10.d4d5 e4e3 11.d5d6 e7d6
```

**draw-rule**
```
n=1  = : 1.a2a4 a7a5
n=2  B : 1.a2a4 a7a5 2.b2b4 a5b4 3.a4a5 b4b3 4.a5a6 b7a6
n=3  = : 1.a2a4 a7a5 2.c2c3 b7b6 3.b2b4 c7c5 4.b4a5 b6a5 5.c3c4
n=4  W : 1.b2b4 a7a5 2.b4a5 b7b5 3.a5b6 c7b6 4.a2a4 b6b5 5.a4b5 d7d5 6.b5b6 d5d4 7.b6b7 d4d3 8.b7b8 (touchdown)
n=5  = : 1.b2b4 d7d5 2.b4b5 d5d4 3.a2a4 a7a5 4.b5a6 b7a6 5.a4a5 d4d3 6.c2d3 c7c5 7.e2e4 c5c4 8.d3c4 e7e5 9.c4c5
```

_This file is regenerated as n = 8 (loss) and n = 7, 8 (draw) complete._
