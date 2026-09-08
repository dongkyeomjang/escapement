#!/usr/bin/env bash
# TASK54 driver: the same trace under both compiled bucket grids.
#
#   run_grid_paired.sh <RUN_DIR>
#
# The point of this experiment is that the grid must not touch the trace, so
# the plan id is pinned per (N, repetition) and every one of the eight
# configurations replays it. run_sweep.sh already knows how to drive one
# combination end to end; this only decides what to hand it, in what order,
# and where each grid's artifacts land.
#
# Preregistered in docs/research/GRID_PAIRED_PREREG.md. Do not edit while a
# sweep is running (TASK23 research principle 1).
set -uo pipefail

RUN="$1"
REPO=/home/rebel/continuum-npu
cd "$REPO"

BASE_SEED=20260954
REPS=3

declare -A ARTIFACT=(
  [mb]="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb"
  [mb6]="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb6"
)
declare -A BUCKETS=( [mb]="1,2,4,8" [mb6]="1,2,4,6,8" )

mkdir -p "$RUN/mb" "$RUN/mb6"

# The order is a preregistered constant, but recompute it from the same
# function rather than pasting it in, so the script and the document cannot
# drift apart silently.
ORDER_FILE="$RUN/order.txt"
env -u PYTHONPATH PYTHONPATH="$REPO/src" python3 - "$BASE_SEED" "$REPS" > "$ORDER_FILE" <<'PY'
import sys
from continuum.workload.paired import balanced_arm_orders
base_seed, rounds = int(sys.argv[1]), int(sys.argv[2])
cfgs = [f"{g}.n{n}.{a}" for g in ("mb", "mb6") for n in (6, 8)
        for a in ("AGENTIC", "CONVENTIONAL")]
for rep, order in enumerate(balanced_arm_orders(cfgs, rounds=rounds,
                                                base_seed=base_seed,
                                                block_id="task54-order")):
    for cfg in order:
        print(rep, cfg)
PY
[ -s "$ORDER_FILE" ] || { echo "order generation failed"; exit 1; }

bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-before.txt" 2>&1
rbln-smi > "$RUN/rbln-smi-before.txt" 2>&1
date -Is > "$RUN/measurement-start.txt"

fail=0
while read -r REP CFG; do
  GRID="${CFG%%.*}"; REST="${CFG#*.}"; NLABEL="${REST%%.*}"; ARM="${REST#*.}"
  N="${NLABEL#n}"
  MODE=$([ "$ARM" = "AGENTIC" ] && echo none || echo zero)
  TAG="${ARM}.n${N}.b${REP}"

  echo "=== rep $REP  $CFG"
  SWEEP_BASE_SEED="$BASE_SEED" \
  SWEEP_ARTIFACT="${ARTIFACT[$GRID]}" \
  SWEEP_BUCKETS="${BUCKETS[$GRID]}" \
  SWEEP_BLOCK_ID="task54-n${N}-r${REP}" \
    bash experiments/npu/stage2/run_sweep.sh "$RUN/$GRID" "$ARM" "$N" "$REP" "$MODE"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "!!! $GRID/$TAG exited $rc"
    fail=$((fail + 1))
    continue
  fi

  env -u PYTHONPATH python3 experiments/npu/analysis/utilization.py \
    --server-log "$RUN/$GRID/server-${TAG}.log" \
    --rows "$RUN/$GRID/probe/requests.${TAG}.jsonl" \
    --meta "$RUN/$GRID/probe/meta.${TAG}.json" \
    --metrics-dump "$RUN/$GRID/metrics-${TAG}.prom" \
    --buckets "${BUCKETS[$GRID]}" --cost-model \
    --label "${GRID}.${TAG}" \
    --output "$RUN/$GRID/util.${TAG}.json" || {
      echo "!!! $GRID/$TAG INVALID (utilization invariants)"
      fail=$((fail + 1))
    }
done < "$ORDER_FILE"

date -Is > "$RUN/measurement-end.txt"
bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-after.txt" 2>&1
rbln-smi > "$RUN/rbln-smi-after.txt" 2>&1
df -h / | tail -1 > "$RUN/disk-after.txt"

echo "combinations with a problem: $fail"
exit 0
