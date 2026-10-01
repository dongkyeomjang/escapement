#!/usr/bin/env bash
# Supplement 2 to run_stepcost_op.sh (TASK92 amendment 2): the multi-turn
# prefill plan op-prefill-mt on every artifact, same runner and arguments,
# 120 s evaluation window (enough exclusive prefills per small-size bin).
#
#   run_stepcost_supp2.sh <RUN_DIR_ABS>      (the same run directory)
set -uo pipefail
RUN="$1"
REPO=/home/rebel/continuum-npu
case "$RUN" in /*) ;; *) echo "RUN must be absolute"; exit 64 ;; esac
S3="$REPO/experiments/npu/stage3"
PLANS="$S3/plans/stepcost"
declare -A ART=(
  [BASE]="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb"
  [BATCHONLY]="$REPO/models/Qwen3-4B-rbln-b16-s8192-d4-batchonly"
  [TUNED]="$REPO/models/Qwen3-4B-rbln-b16-s8192-d4-mb16"
  [DP]="$REPO/models/Qwen3-4B-rbln-b16-s8192-d4-dp8"
)
git -C "$REPO" rev-parse HEAD >> "$RUN/git-head.txt"
date -Is > "$RUN/supplement2-start.txt"
for CFG in TUNED BASE DP BATCHONLY; do
  TAG="$CFG.op-prefill-mt"
  echo "=== $TAG $(date -Is)"
  bash "$S3/run_multiturn.sh" "$RUN" "$TAG" "${ART[$CFG]}" "$PLANS/op-prefill-mt.json" stream 120
  if [ ! -f "$RUN/done.$TAG" ]; then
    echo "$TAG failed, retrying once"
    bash "$S3/run_multiturn.sh" "$RUN" "$TAG.retry1" "${ART[$CFG]}" "$PLANS/op-prefill-mt.json" stream 120
  fi
done
date -Is > "$RUN/supplement2-end.txt"
echo "SUPPLEMENT2 DONE"
