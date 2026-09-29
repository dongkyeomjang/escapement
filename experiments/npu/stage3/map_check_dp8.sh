#!/usr/bin/env bash
# Bucket mapping check of the DP(8) artifact, the way TASK23/TASK34 did it:
# fire k simultaneous requests for k in 2,3,5,6,7 and read the [BUCKET] lines.
# Expected under bisect_left on (1,2,3,4,6,16): 2->2, 3->3, 5->6, 6->6, 7->16.
#
#   map_check_dp8.sh <RUN_DIR_ABS>
set -uo pipefail
RUN="$1"
REPO=/home/rebel/continuum-npu
case "$RUN" in /*) ;; *) echo "RUN must be absolute"; exit 64 ;; esac
cd "$REPO"
ART="$REPO/models/Qwen3-4B-rbln-b16-s8192-d4-dp8"
M="$RUN/mapping"
mkdir -p "$M"
cp "$REPO/results/npu/stage2/20260823-170201-compile-config/mapping/prompt.txt" "$M/prompt.txt"
bash patches/vllm_rbln-0.11.1/apply.sh status > "$M/patch-state.txt" 2>&1
date -Is > "$M/started_at.txt"

env -u PYTHONPATH VLLM_LOGGING_LEVEL=DEBUG VLLM_RBLN_METRICS=1 \
  vllm serve "$ART" --host 127.0.0.1 --port 8000 \
  --enable-prefix-caching --enable-prompt-tokens-details > "$M/server.log" 2>&1 &
SRV=$!
code=""
for i in $(seq 1 300); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null)
  [ "$code" = "200" ] && break
  kill -0 "$SRV" 2>/dev/null || { echo "server died"; exit 1; }
  sleep 1
done
[ "$code" = "200" ] || { echo "health timeout"; kill -TERM "$SRV"; exit 1; }

env -u PYTHONPATH "$REPO/experiments/npu/launch/run_isolated_python.sh" \
  experiments/npu/stage1/concurrency_probe.py --base-url http://127.0.0.1:8000 \
  --prompt-file "$M/prompt.txt" --max-tokens 64 --seed 20261430 --levels 2,3,5,6,7 \
  --output-dir "$M" > "$M/probe.log" 2>&1
PE=$?
curl -s http://127.0.0.1:8000/metrics > "$M/metrics.prom"
kill -TERM "$SRV" 2>/dev/null
for i in $(seq 1 60); do kill -0 "$SRV" 2>/dev/null || break; sleep 1; done
if kill -0 "$SRV" 2>/dev/null; then kill -KILL "$SRV" 2>/dev/null; sleep 5; echo "server needed SIGKILL"; fi
wait "$SRV" 2>/dev/null
date -Is > "$M/finished_at.txt"
echo "probe exit $PE"
grep -o "Bucket sizes for RBLN sampler: ([0-9, ]*)" "$M/server.log" | head -1
grep -o "\[BUCKET\] request_nums=[0-9]* padded_batch_size=[0-9]*" "$M/server.log" | sort | uniq -c
