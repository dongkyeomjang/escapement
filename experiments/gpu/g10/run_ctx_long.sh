#!/usr/bin/env bash
# G-10 C long-context step-cost microbenchmark (prereg docs/research/gpu/G10_CTX_LONG_PREREG.md).
# Lifecycles r0, r1; an INVALID lifecycle is rerun once; analysis once; the
# summary is copied to experiments/gpu/g10/ctx_long_result/ (committed by hand).
# usage: run_ctx_long.sh <ABS_RUN_DIR>. Do not edit while running.
set -uo pipefail
RUN="${1:?usage: run_ctx_long.sh <abs run dir>}"
case "$RUN" in /*) ;; *) echo "run dir must be absolute" >&2; exit 2 ;; esac
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python
D="$REPO/experiments/gpu/g10"
mkdir -p "$RUN"
git -C "$REPO" rev-parse HEAD > "$RUN/start_commit.txt"
date -u -Is > "$RUN/start.txt"
for rep in 0 1; do
  echo "$(date -u -Is) start r$rep" | tee -a "$RUN/sequence.log"
  rc=0
  env -u PYTHONPATH "$PY" "$D/ctx_long_run.py" --rep "$rep" --out-dir "$RUN/r$rep" > "$RUN/r$rep.stdout" 2>&1 || rc=$?
  echo "$(date -u -Is) end r$rep rc=$rc" | tee -a "$RUN/sequence.log"
done
for rep in 0 1; do
  ok=$("$PY" -c "import json;print(json.load(open('$RUN/r$rep/summary.json'))['valid'])" 2>/dev/null || echo False)
  if [ "$ok" != "True" ]; then
    mv "$RUN/r$rep" "$RUN/r$rep.invalid0"
    echo "$(date -u -Is) start r$rep.retry1" | tee -a "$RUN/sequence.log"
    rc=0
    env -u PYTHONPATH "$PY" "$D/ctx_long_run.py" --rep "$rep" --out-dir "$RUN/r$rep.retry1" > "$RUN/r$rep.retry1.stdout" 2>&1 || rc=$?
    echo "$(date -u -Is) end r$rep.retry1 rc=$rc" | tee -a "$RUN/sequence.log"
  fi
done
rc=0
env -u PYTHONPATH "$PY" "$D/ctx_long_analyze.py" --run-dir "$RUN" --out "$RUN/summary.json" > "$RUN/analyze.stdout" 2>&1 || rc=$?
echo "$(date -u -Is) analyzed rc=$rc" | tee -a "$RUN/sequence.log"
mkdir -p "$D/ctx_long_result" && cp "$RUN/summary.json" "$D/ctx_long_result/summary.json"
echo "$(date -u -Is) done" | tee -a "$RUN/sequence.log"
