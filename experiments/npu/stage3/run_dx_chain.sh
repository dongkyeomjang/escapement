#!/usr/bin/env bash
# Chain of the measured orders after work A (DX_PREREG.md §3.2–3.3):
# B -> C -> [time rule] B extension -> [time rule] E. Each extension starts only if
#   now + lifecycles x 4.5 min + 2 h <= 2026-10-10 14:59 KST
# (decided from the clock alone; logged in <BASE>/chain.log).
#
#   run_dx_chain.sh <RESULTS_BASE_ABS>
set -uo pipefail
BASE="$1"
S3=/home/rebel/continuum-npu/experiments/npu/stage3
PL="$S3/plans/dx"
LIMIT=$(date -d "2026-10-10 14:59 KST" +%s)
log() { echo "$(date -Is) $*" | tee -a "$BASE/chain.log"; }
allowed() {  # n_lifecycles
  local need=$(( $(date +%s) + $1 * 270 + 7200 ))
  [ "$need" -le "$LIMIT" ]
}
log "chain start"
bash "$S3/run_dx.sh" "$BASE/20261008-dx-b" "$PL/ORDER_DXB.json" > "$BASE/20261008-dx-b.run.log" 2>&1; log "B done"
bash "$S3/run_dx.sh" "$BASE/20261008-dx-c" "$PL/ORDER_DXC_OBSOFF.json" > "$BASE/20261008-dx-c.run.log" 2>&1; log "C done"
if allowed 20; then
  log "B8 allowed by time rule"; bash "$S3/run_dx.sh" "$BASE/20261008-dx-b8" "$PL/ORDER_DXB8.json" > "$BASE/20261008-dx-b8.run.log" 2>&1; log "B8 done"
else log "B8 NOT started: time rule"; fi
if allowed 30; then
  log "E allowed by time rule"; bash "$S3/run_dx.sh" "$BASE/20261008-dx-e" "$PL/ORDER_DXE.json" > "$BASE/20261008-dx-e.run.log" 2>&1; log "E done"
else log "E NOT started: time rule"; fi
log "chain end"
