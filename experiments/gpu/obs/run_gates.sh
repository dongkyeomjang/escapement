#!/usr/bin/env bash
# GTASK03 gate sequence (prereg: docs/research/gpu/GPU_OBS_GATE_PREREG.md).
#   1. arm A on the pristine install
#   2. apply the observation patch (hash-guarded)
#   3. arm B on the patched install (ESCAPEMENT_OBS=1, KV events + collector)
#   4. revert (G3) and record SHA256
#   5. judge G1-G3
# usage: run_gates.sh <ABS_RUN_DIR>. Do not edit while running (KNOWN_PITFALLS 5).
set -euo pipefail
RUN="${1:?usage: run_gates.sh <abs run dir>}"
case "$RUN" in /*) ;; *) echo "run dir must be absolute" >&2; exit 2 ;; esac
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python
PATCH="$REPO/experiments/gpu/patches/vllm-0.22.0/apply.sh"
mkdir -p "$RUN"
log() { echo "$(date -u -Is) $*" | tee -a "$RUN/sequence.log"; }

log "status before"; bash "$PATCH" status | tee -a "$RUN/sequence.log"
log "arm A start"; env -u PYTHONPATH "$PY" "$REPO/experiments/gpu/obs/gate_run.py" --arm A --out-dir "$RUN/A" > "$RUN/A.stdout" 2>&1; log "arm A done"
log "apply"; bash "$PATCH" apply | tee -a "$RUN/sequence.log"
log "arm B start"; env -u PYTHONPATH "$PY" "$REPO/experiments/gpu/obs/gate_run.py" --arm B --out-dir "$RUN/B" > "$RUN/B.stdout" 2>&1; log "arm B done"
log "revert"; { bash "$PATCH" revert; bash "$PATCH" status; } > "$RUN/revert.log" 2>&1; cat "$RUN/revert.log" | tee -a "$RUN/sequence.log"
log "judge"; env -u PYTHONPATH "$PY" "$REPO/experiments/gpu/obs/gate_judge.py" --a "$RUN/A" --b "$RUN/B" --revert-log "$RUN/revert.log" --out "$RUN/verdict.json" | tee -a "$RUN/sequence.log"
