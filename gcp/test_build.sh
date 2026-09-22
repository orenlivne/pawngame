#!/bin/bash
# Cheap build smoke-test: build on x86 Linux, run a tiny solve, upload PASS/FAIL,
# self-delete. Run this on an e2-small before committing to the big machine.
set -x
exec > /var/log/test.log 2>&1
meta(){ curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/$1"; }
BUCKET=$(meta attributes/bucket); NAME=$(meta name); ZONE=$(meta zone | awk -F/ '{print $NF}')
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get install -y clang
cd /root
gsutil cp gs://$BUCKET/pawngame.tar.gz . && tar xzf pawngame.tar.gz && cd pawngame
R=/tmp/test_result.txt; : > $R
clang++ -O3 -std=c++17 -pthread -mcx16 -latomic -o pp src/cpp/pawnsolver_par.cpp 2>/tmp/build.err \
  && echo "BUILD_OK ($(nproc) cores)" >> $R || { echo "BUILD_FAIL"; head -8 /tmp/build.err >> $R; }
# Parallel-scaling check: if threads scale, the x86 128-bit atomics are effectively
# lock-free (cmpxchg16b). If t=all is not much faster than t=1, they are lock-bound.
echo "n7 loss t1 : $(./pp 7 loss --colorsym --minsub=16 --threads=1  2>&1 | grep -o 'value=.*/s)')" >> $R
echo "n7 loss t$(nproc): $(./pp 7 loss --colorsym --minsub=16 --threads=$(nproc) 2>&1 | grep -o 'value=.*/s)')" >> $R
gsutil cp $R gs://$BUCKET/test_result.txt
gsutil cp /var/log/test.log gs://$BUCKET/test.log
gcloud compute instances delete $NAME --zone $ZONE --quiet
