#!/bin/bash
# Reproduce the results in the paper.
#   ./reproduce.sh values      re-solve all n=1..7, both rules, with and without e.p.
#   ./reproduce.sh tests       run the test suite (oracle fuzz + cross-validation)
#   ./reproduce.sh stockfish   tablebase-vs-Stockfish play-test, winning side (needs stockfish)
#   ./reproduce.sh all         all of the above
# (n=8 loss fits in ~25 GB; draw-rule n=8 needs a big-memory machine -- see gcp/.)
set -e
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/src" PAWN_SRV="$PWD/src/cpp/pawnsolver_par"
BIN=src/cpp/pawnsolver_par
NC=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)
bits(){ case $1 in 5) echo 25;; 6) echo 28;; 7) echo 31;; 8) echo 33;; *) echo 22;; esac; }

need_bin(){ [ -x "$BIN" ] || { echo "Build the solver first:  make"; exit 1; }; }

values(){
  need_bin
  echo "### Game values (n=1..7, both rules) -- with en passant"
  for r in loss draw; do for n in 1 2 3 4 5 6 7; do
    "$BIN" $n $r --colorsym --threads=$NC --minsub=16 --bits=$(bits $n) | grep -E "value="
  done; done
  echo "### Game values -- WITHOUT en passant (the essentiality table)"
  for r in loss draw; do for n in 1 2 3 4 5 6 7; do
    "$BIN" $n $r --colorsym --threads=$NC --minsub=16 --bits=$(bits $n) --noep | grep -E "value="
  done; done
  echo "### n=8: loss fits in ~25 GB:  $BIN 8 loss --colorsym --threads=$NC --minsub=16 --bits=33"
  echo "### n=8 draw needs ~256 GB RAM -- see gcp/startup.sh"
}

tests(){ need_bin; PYTHONPATH="$PWD/src" pytest -q; }

stockfish(){
  need_bin
  command -v stockfish >/dev/null || { echo "stockfish not found on PATH"; exit 1; }
  echo "### Tablebase vs Stockfish (winning/non-losing side, 100 games, depth 12)"
  for r in loss draw; do for n in 1 2 3 4 5 6 7; do
    python3 -m pawn.exact.play_batch_cpp $n $r --games 100 --depth 12 --side auto \
      --extra "--colorsym --minsub=16 --bits=$(bits $n) --threads=$NC"
  done; done
}

case "${1:-all}" in
  values) values ;;
  tests) tests ;;
  stockfish) stockfish ;;
  all) values; tests; stockfish ;;
  *) echo "usage: $0 {values|tests|stockfish|all}"; exit 1 ;;
esac
