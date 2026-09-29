#!/usr/bin/env bash
# GTASK05 step-cost lifecycles (prereg: docs/research/gpu/GPU_STEPCOST_PREREG.md).
# Order: G1 r0, G2 r0, G3 r0, G1 r1, G2 r1, G3 r1, then the analysis.
# usage: run_stepcost.sh <ABS_RUN_DIR>. Do not edit while running (KNOWN_PITFALLS 5).
set -euo pipefail
RUN="${1:?usage: run_stepcost.sh <abs run dir>}"
case "$RUN" in /*) ;; *) echo "run dir must be absolute" >&2; exit 2 ;; esac
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python
mkdir -p "$RUN"
for rep in 0 1; do
  for g in G1 G2 G3; do
    echo "$(date -u -Is) start $g r$rep" | tee -a "$RUN/sequence.log"
    rc=0
    env -u PYTHONPATH "$PY" "$REPO/experiments/gpu/stepcost/stepcost_run.py" --grid "$g" --rep "$rep" \
      --out-dir "$RUN/${g}_r${rep}" > "$RUN/${g}_r${rep}.stdout" 2>&1 || rc=$?
    echo "$(date -u -Is) end $g r$rep rc=$rc" | tee -a "$RUN/sequence.log"
  done
done
env -u PYTHONPATH "$PY" "$REPO/experiments/gpu/stepcost/stepcost_analyze.py" --run-dir "$RUN" \
  --out "$RUN/summary.json" --md "$RUN/summary.md" > "$RUN/analyze.stdout" 2>&1
echo "$(date -u -Is) analyzed" | tee -a "$RUN/sequence.log"
