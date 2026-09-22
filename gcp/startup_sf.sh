#!/bin/bash
# SF-only run: build the solver, then play the tablebase-vs-Stockfish games for
# every hosted row (n=1..7 both rules + n=8 loss) on this one 256 GB machine so the
# whole play-test is uniform. Fail fast if Stockfish is not runnable. Upload the log
# after each config; self-delete at the end. max-run-duration is the cost backstop.
set -x
exec > /var/log/pawn-sf.log 2>&1
meta(){ curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/$1"; }
BUCKET=$(meta attributes/bucket); NAME=$(meta name); ZONE=$(meta zone | awk -F/ '{print $NF}')
RES=/tmp/sf_results.txt; : > $RES
push(){ gsutil -q cp $RES gs://$BUCKET/stockfish_playtest.txt; gsutil -q cp /var/log/pawn-sf.log gs://$BUCKET/sf.log; }
selfdelete(){ gcloud compute instances delete $NAME --zone $ZONE --quiet; }

export DEBIAN_FRONTEND=noninteractive
export PATH=/usr/games:$PATH        # Debian installs stockfish under /usr/games
apt-get update -y
apt-get install -y clang stockfish python3-pip
pip3 install --break-system-packages python-chess 2>/dev/null || pip3 install python-chess

# Fail fast: Stockfish must be runnable, or the whole run is pointless.
SF=$(command -v stockfish || echo /usr/games/stockfish)
if ! "$SF" bench 1 1 1 >/dev/null 2>&1 && ! echo quit | "$SF" >/dev/null 2>&1; then
  echo "### FATAL: Stockfish not runnable ($SF)" >> $RES; push; selfdelete; exit 1
fi
echo "# host: $(nproc)vCPU $(free -g | awk '/Mem/{print $2}')GB (n2-highmem-32); stockfish: $SF; $(date -u)" >> $RES
push

cd /root
gsutil cp gs://$BUCKET/pawngame.tar.gz . && tar xzf pawngame.tar.gz && cd pawngame
clang++ -O3 -std=c++17 -pthread -mcx16 -latomic -o src/cpp/pawnsolver_par src/cpp/pawnsolver_par.cpp
cp src/cpp/pawnsolver_par src/cpp/pawnsolver_srv
export PAWN_SRV=$PWD/src/cpp/pawnsolver_srv PYTHONPATH=$PWD/src
NC=$(nproc)

bits(){ case $1 in 5) echo 25;; 6) echo 28;; 7) echo 31;; 8) echo 33;; *) echo 22;; esac; }
sf(){ # n rule
  echo "### SF n=$1 rule=$2" >> $RES
  python3 -m pawn.exact.play_batch_cpp $1 $2 --games 100 --depth 12 --side auto \
    --extra "--colorsym --minsub=16 --bits=$(bits $1) --threads=$NC" >> $RES 2>>/var/log/pawn-sf.log
  push
}

for r in loss draw; do for n in 1 2 3 4 5 6 7; do sf $n $r; done; done   # all n<=7, both rules
sf 8 loss                                                               # the 24.8 GB table fits in 256 GB
echo "### ALL DONE $(date -u)" >> $RES; push
selfdelete
