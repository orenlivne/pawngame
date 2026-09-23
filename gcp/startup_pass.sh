#!/bin/bash
# Solve the PASS rule variant (a player may pass, but not right after the opponent
# passed) for n=1..8 under both rulesets, then run the tablebase-vs-Stockfish
# play-test for it. Upload after each step; self-delete at the end. The pass bit
# roughly doubles the state space, so this is heavier than the base game.
set -x
exec > /var/log/pawn-pass.log 2>&1
meta(){ curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/$1"; }
BUCKET=$(meta attributes/bucket); NAME=$(meta name); ZONE=$(meta zone | awk -F/ '{print $NF}')
RES=/tmp/pass_results.txt; : > $RES
push(){ gsutil -q cp $RES gs://$BUCKET/pass_results.txt; gsutil -q cp /var/log/pawn-pass.log gs://$BUCKET/pass.log; }
selfdelete(){ gcloud compute instances delete $NAME --zone $ZONE --quiet; }

export DEBIAN_FRONTEND=noninteractive
export PATH=/usr/games:$PATH
apt-get update -y
apt-get install -y clang stockfish python3-pip
pip3 install --break-system-packages python-chess 2>/dev/null || pip3 install python-chess
SF=$(command -v stockfish || echo /usr/games/stockfish)
if ! echo quit | "$SF" >/dev/null 2>&1; then echo "### FATAL: no stockfish" >> $RES; push; selfdelete; exit 1; fi

cd /root
gsutil cp gs://$BUCKET/pawngame.tar.gz . && tar xzf pawngame.tar.gz && cd pawngame
clang++ -O3 -std=c++17 -pthread -mcx16 -latomic -o src/cpp/pawnsolver_par src/cpp/pawnsolver_par.cpp
cp src/cpp/pawnsolver_par src/cpp/pawnsolver_srv
export PAWN_SRV=$PWD/src/cpp/pawnsolver_srv PYTHONPATH=$PWD/src
NC=$(nproc)
echo "### MACHINE $(nproc)vCPU $(free -g|awk '/Mem/{print $2}')GB $(date -u)" >> $RES; push

# minsub/bits per n for the pass variant (roughly 2x the base game's state).
bits(){ case $1 in 5) echo 26;; 6) echo 29;; 7) echo 32;; 8) echo 33;; *) echo 22;; esac; }
minsub(){ case $1 in 8) echo 128;; 7) echo 32;; *) echo 16;; esac; }
solve(){ # n rule
  echo "### SOLVE n=$1 rule=$2 --pass minsub=$(minsub $1)" >> $RES
  ./src/cpp/pawnsolver_par $1 $2 --pass --colorsym --threads=$NC --minsub=$(minsub $1) --bits=$(bits $1) >> $RES 2>>/var/log/pawn-pass.log
  push
}
sf(){ # n rule
  echo "### SF-PASS n=$1 rule=$2 winning-side" >> $RES
  python3 -m pawn.exact.play_pass_cpp $1 $2 --games 100 --depth 12 --side auto \
     --extra "--pass --colorsym --minsub=$(minsub $1) --bits=$(bits $1) --threads=$NC" >> $RES 2>>/var/log/pawn-pass.log
  push
}

# Values first (cheap n<=4 are quick; 5..8 are the work). loss n=8 (White) before
# the expensive draw n=8 so we bank the headline value early.
for r in loss draw; do for n in 1 2 3 4 5 6 7; do solve $n $r; done; done
solve 8 loss
solve 8 draw
# Stockfish never-lose check (n<=7 both rules + n=8 loss).
for r in loss draw; do for n in 1 2 3 4 5 6 7; do sf $n $r; done; done
sf 8 loss
echo "### ALL DONE $(date -u)" >> $RES; push
selfdelete
