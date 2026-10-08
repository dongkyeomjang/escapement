#!/usr/bin/env bash
# G-10 A exec-timing ON/OFF development check (prereg docs/research/gpu/G10_A_PREREG.md).
# Runs exec_check_order.json, reruns an INVALID lifecycle once (after the order),
# analyses once. Results stay under the run dir; summary copied to
# experiments/gpu/g10/exec_check_result/ (committed by hand).
# usage: run_exec_check.sh <ABS_RUN_DIR>. Do not edit while running.
set -uo pipefail
RUN="${1:?usage: run_exec_check.sh <abs run dir>}"
case "$RUN" in /*) ;; *) echo "run dir must be absolute" >&2; exit 2 ;; esac
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python
D="$REPO/experiments/gpu/g10"
mkdir -p "$RUN"
git -C "$REPO" rev-parse HEAD > "$RUN/start_commit.txt"
date -u -Is > "$RUN/start.txt"
env -u PYTHONPATH "$PY" - "$D/exec_check_order.json" > "$RUN/order.tsv" <<'PYEOF'
import json, sys
for e in json.load(open(sys.argv[1])):
    print(e["tag"], e["config"], e["load"], e["exec"], e["pair"])
PYEOF
run_one() {  # tag cfg load exec pair outdir
  echo "$(date -u -Is) start $6" | tee -a "$RUN/sequence.log"
  rc=0
  env -u PYTHONPATH "$PY" "$D/exec_check_run.py" --config "$2" --load "$3" --exec "$4" --pair "$5" \
    --out-dir "$RUN/$6" > "$RUN/$6.stdout" 2>&1 || rc=$?
  echo "$(date -u -Is) end $6 rc=$rc" | tee -a "$RUN/sequence.log"
}
while read -r tag cfg load x k; do run_one "$tag" "$cfg" "$load" "$x" "$k" "$tag"; done < "$RUN/order.tsv"
while read -r tag cfg load x k; do
  ok=$("$PY" -c "import json;print(json.load(open('$RUN/$tag/summary.json'))['valid'])" 2>/dev/null || echo False)
  if [ "$ok" != "True" ]; then run_one "$tag" "$cfg" "$load" "$x" "$k" "$tag.retry1"; fi
done < "$RUN/order.tsv"
rc=0
env -u PYTHONPATH "$PY" "$D/exec_check_analyze.py" --run-dir "$RUN" --out "$RUN/summary.json" > "$RUN/analyze.stdout" 2>&1 || rc=$?
echo "$(date -u -Is) analyzed rc=$rc" | tee -a "$RUN/sequence.log"
mkdir -p "$D/exec_check_result" && cp "$RUN/summary.json" "$D/exec_check_result/summary.json"
echo "$(date -u -Is) done" | tee -a "$RUN/sequence.log"
