#!/usr/bin/env bash
# Chain after the repeated work A check (DX_PREREG §12):
#   run_dx_chain2.sh <RESULTS_BASE_ABS> <on|off>
# on  (repeat check WITHIN_1PCT): ORDER_DXB, ORDER_DXB8, ORDER_DXE with OBS on
# off (repeat check PERTURBATION): the *_OBSOFF orders (B direct BLOCKED)
# B always; B extension and E each only if
#   now + lifecycles x 4.5 min + 2 h <= 2026-10-10 14:59 KST   (clock only)
set -uo pipefail
BASE="$1"; MODE="$2"
case "$MODE" in on) SUF="" ;; off) SUF="_OBSOFF" ;; *) echo "mode on|off"; exit 64 ;; esac
S3=/home/rebel/continuum-npu/experiments/npu/stage3
PL="$S3/plans/dx"
LIMIT=$(date -d "2026-10-10 14:59 KST" +%s)
log() { echo "$(date -Is) $*" | tee -a "$BASE/chain2.log"; }
allowed() { [ $(( $(date +%s) + $1 * 270 + 7200 )) -le "$LIMIT" ]; }
log "chain2 start mode=$MODE"
bash "$S3/run_dx.sh" "$BASE/20261008-dx-b" "$PL/ORDER_DXB$SUF.json" > "$BASE/20261008-dx-b.run.log" 2>&1; log "B done"
if allowed 20; then log "B8 allowed by time rule"
  bash "$S3/run_dx.sh" "$BASE/20261008-dx-b8" "$PL/ORDER_DXB8$SUF.json" > "$BASE/20261008-dx-b8.run.log" 2>&1; log "B8 done"
else log "B8 NOT started: time rule"; fi
if allowed 30; then log "E allowed by time rule"
  bash "$S3/run_dx.sh" "$BASE/20261008-dx-e" "$PL/ORDER_DXE$SUF.json" > "$BASE/20261008-dx-e.run.log" 2>&1; log "E done"
else log "E NOT started: time rule"; fi
log "chain2 end"
