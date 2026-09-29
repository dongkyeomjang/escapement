#!/usr/bin/env bash
# Streaming observer-effect pilot: 12 lifecycles in the preregistered order
# (docs/research/STREAMING_PILOT_PREREG.md). Do not edit while running.
set -uo pipefail
RUN="$1"   # absolute
REPO=/home/rebel/continuum-npu
case "$RUN" in /*) ;; *) echo "RUN must be absolute"; exit 64 ;; esac
mkdir -p "$RUN"
BASE_ART="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb"
TUNED_ART="$REPO/models/Qwen3-4B-rbln-b16-s8192-d4-mb16"
PLANS="$REPO/experiments/npu/stage3/plans"
git -C "$REPO" rev-parse HEAD > "$RUN/git-head.txt"
date -Is > "$RUN/measurement-start.txt"
rbln-stat > "$RUN/rbln-stat-before.txt" 2>&1
bash "$REPO/patches/vllm_rbln-0.11.1/apply.sh" status > "$RUN/patch-before.txt" 2>&1
ORDER=(
  "0 BASE nostream" "0 BASE stream" "0 TUNED stream" "0 TUNED nostream"
  "1 TUNED nostream" "1 TUNED stream" "1 BASE stream" "1 BASE nostream"
  "2 BASE stream" "2 BASE nostream" "2 TUNED nostream" "2 TUNED stream"
)
for item in "${ORDER[@]}"; do
  set -- $item
  R="$1"; CFG="$2"; MODE="$3"
  if [ "$CFG" = BASE ]; then ART="$BASE_ART"; else ART="$TUNED_ART"; fi
  TAG="${CFG}.${MODE}.r${R}"
  echo "=== $TAG $(date -Is)"
  bash "$REPO/experiments/npu/stage3/run_multiturn.sh" "$RUN" "$TAG" "$ART" \
    "$PLANS/pilot-n8-r${R}.json" "$MODE"
done
date -Is > "$RUN/measurement-end.txt"
rbln-stat > "$RUN/rbln-stat-after.txt" 2>&1
bash "$REPO/patches/vllm_rbln-0.11.1/apply.sh" status > "$RUN/patch-after.txt" 2>&1
echo "PILOT DONE"
