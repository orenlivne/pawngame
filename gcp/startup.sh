#!/bin/bash
# GCP VM startup script: build the solver, run every solve (both rulesets, with
# and without en passant) plus Stockfish on the winning side, upload results to
# GCS after each step, then self-delete. A --max-run-duration on the instance is
# the hard backstop so cost is bounded even if this script hangs.
set -x
exec > /var/log/pawn-run.log 2>&1
meta(){ curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/$1"; }
BUCKET=$(meta attributes/bucket)
NAME=$(meta name)
ZONE=$(meta zone | awk -F/ '{print $NF}')
RES=/tmp/results.txt; : > $RES
push(){ gsutil -q cp $RES gs://$BUCKET/results.txt; gsutil -q cp /var/log/pawn-run.log gs://$BUCKET/run.log; }

export DEBIAN_FRONTEND=noninteractive
export PATH=/usr/games:$PATH   # Debian installs stockfish under /usr/games
apt-get update -y
apt-get install -y clang stockfish python3-pip
pip3 install --break-system-packages python-chess 2>/dev/null || pip3 install python-chess

cd /root
gsutil cp gs://$BUCKET/pawngame.tar.gz .
tar xzf pawngame.tar.gz
cd pawngame
clang++ -O3 -std=c++17 -pthread -mcx16 -latomic -o src/cpp/pawnsolver_par src/cpp/pawnsolver_par.cpp
cp src/cpp/pawnsolver_par src/cpp/pawnsolver_srv
export PAWN_SRV=$PWD/src/cpp/pawnsolver_srv PYTHONPATH=$PWD/src
NC=$(nproc)

bits(){ case $1 in 5) echo 25;; 6) echo 28;; 7) echo 31;; 8) echo 33;; *) echo 22;; esac; }
solve(){ # n rule minsub extra
  echo "### SOLVE n=$1 rule=$2 minsub=$3 $4" >> $RES
  ./src/cpp/pawnsolver_par $1 $2 --colorsym --threads=$NC --minsub=$3 --bits=$(bits $1) $4 --pv >> $RES 2>>/var/log/pawn-run.log
  push
}
sf(){ # n rule
  echo "### SF n=$1 rule=$2 winning-side" >> $RES
  python3 -m pawn.exact.play_batch_cpp $1 $2 --games 100 --depth 12 --side auto \
     --extra "--colorsym --minsub=16 --bits=$(bits $1) --threads=$NC" >> $RES 2>>/var/log/pawn-run.log
  push
}

echo "### MACHINE $(nproc)vCPU $(free -g|awk '/Mem/{print $2}')GB $(date)" >> $RES; push

# Priority order; each result is uploaded immediately.
solve 8 draw 64 ""                 # P1: the missing draw-n8 value (~137 GB table)
solve 8 loss 16 ""                 # P2: loss-n8 (emits both 1.c4 and 1.b4 lines)
for r in loss draw; do for n in 1 2 3 4 5 6 7; do solve $n $r 16 ""; done; done   # P3: n<=7 ep
for r in loss draw; do for n in 1 2 3 4 5 6 7; do solve $n $r 16 "--noep"; done; done  # P4: no-e.p.
solve 8 loss 16 "--noep"
solve 8 draw 64 "--noep"
sf 7 loss; sf 7 draw; sf 8 loss    # P5: Stockfish winning-side (n<=6 already done on the reference machine)

echo "### ALL DONE $(date)" >> $RES; push
gcloud compute instances delete $NAME --zone $ZONE --quiet
