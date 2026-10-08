#!/usr/bin/env bash
# G-10 chain: wait for the task-A check run to finish; if its preregistered
# overall verdict is OK, run B (run_b.sh) and then C (run_c.sh). Otherwise stop
# (B prereg section 0: an EXCEEDS result needs an amended prereg first).
# usage: run_chain.sh <ABS_A_RUN_DIR> <ABS_B_RUN_DIR> <ABS_C_RUN_DIR>
set -uo pipefail
A="$1"; B="$2"; C="$3"
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python
LOG="$(dirname "$B")/chain.log"
until grep -q ' done$' "$A/sequence.log" 2>/dev/null; do sleep 20; done
ov=$("$PY" -c "import json;print(json.load(open('$A/summary.json'))['overall'])" 2>/dev/null || echo ERROR)
echo "$(date -u -Is) A overall=$ov" | tee -a "$LOG"
[ "$ov" = "OK" ] || { echo "$(date -u -Is) stop: A not OK" | tee -a "$LOG"; exit 3; }
"$D/run_b.sh" "$B" > "$B.outer.log" 2>&1
echo "$(date -u -Is) B finished rc=$?" | tee -a "$LOG"
"$D/run_c.sh" "$C" > "$C.outer.log" 2>&1
echo "$(date -u -Is) C finished rc=$?" | tee -a "$LOG"
