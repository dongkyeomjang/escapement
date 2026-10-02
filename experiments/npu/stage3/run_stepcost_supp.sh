#!/usr/bin/env bash
# Supplement to run_stepcost_op.sh (TASK92 amendment): the lifecycles whose
# 10-session plan ran out -- n = 1 for every artifact and DP n = 2 -- with the
# 30-session plans op-decode-n{1,2}-s30. Same runner, arguments, 40 s window.
#
#   run_stepcost_supp.sh <RUN_DIR_ABS>      (the same run directory)
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
date -Is > "$RUN/supplement-start.txt"
for item in "DP op-decode-n1-s30" "BASE op-decode-n1-s30" "TUNED op-decode-n1-s30" \
            "DP op-decode-n2-s30" "BATCHONLY op-decode-n1-s30"; do
  set -- $item
  CFG="$1"; PID="$2"; TAG="$CFG.$PID"
  echo "=== $TAG $(date -Is)"
  bash "$S3/run_multiturn.sh" "$RUN" "$TAG" "${ART[$CFG]}" "$PLANS/$PID.json" stream 40
  if [ ! -f "$RUN/done.$TAG" ]; then
    echo "$TAG failed, retrying once"
    bash "$S3/run_multiturn.sh" "$RUN" "$TAG.retry1" "${ART[$CFG]}" "$PLANS/$PID.json" stream 40
  fi
done
date -Is > "$RUN/supplement-end.txt"
echo "SUPPLEMENT DONE"
