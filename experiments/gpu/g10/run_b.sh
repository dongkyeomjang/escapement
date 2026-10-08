#!/usr/bin/env bash
# G-10 B (prereg docs/research/gpu/G10_B_PREREG.md). 1. plans_b/ORDER_B.json, every
# lifecycle with --stream --exec-timing; 2. rerun once (.retry1, after the order)
# a lifecycle that is INVALID without preemption, or valid with an incomplete
# DIRECT channel; a lifecycle with preemption is never rerun; 3. judge_b.py once;
# 4. commit ONLY experiments/gpu/g10/b_result/verdict.json to local gpu-a6000.
# usage: run_b.sh <ABS_RUN_DIR>. Do not edit the scripts while it runs.
set -uo pipefail
RUN="${1:?usage: run_b.sh <abs run dir>}"
case "$RUN" in /*) ;; *) echo "run dir must be absolute" >&2; exit 2 ;; esac
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python
D="$REPO/experiments/gpu/g10"
MT="$REPO/experiments/gpu/multiturn"
mkdir -p "$RUN"
git -C "$REPO" rev-parse HEAD > "$RUN/start_commit.txt"
date -u -Is > "$RUN/start.txt"
env -u PYTHONPATH "$PY" - "$D/plans_b/ORDER_B.json" > "$RUN/order.tsv" <<'PYEOF'
import json, sys
for e in json.load(open(sys.argv[1])):
    print(e["tag"], e["plan"], e["config"], e["n"])
PYEOF
run_one() {  # tag plan cfg n dir
  echo "$(date -u -Is) start $5" | tee -a "$RUN/sequence.log"
  rc=0
  "$PY" "$MT/gpu_mt_runner.py" --plan "$2" --config "$3" --n "$4" --out-dir "$RUN/$5" --stream --exec-timing \
    > "$RUN/$5.stdout" 2>&1 || rc=$?
  echo "$(date -u -Is) end $5 rc=$rc" | tee -a "$RUN/sequence.log"
}
while read -r tag plan cfg n; do run_one "$tag" "$plan" "$cfg" "$n" "$tag"; done < "$RUN/order.tsv"
env -u PYTHONPATH "$PY" - "$RUN" "$D" <<'PYEOF' > "$RUN/retry_list.txt" 2>> "$RUN/driver.log"
import sys
from pathlib import Path
run, d = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(d))
import judge_b as J
for line in (run / "order.tsv").read_text().splitlines():
    tag, plan, cfg, n = line.split()
    p = run / tag
    retry = True
    if (p / "windows.json").exists():
        try:
            L = J.load(p)
            retry = (not L["valid"] and L["preemptions"] == 0) or (L["valid"] and not L["direct_ok"])
        except Exception as ex:
            print(f"# {tag} metrics error {ex!r}", file=sys.stderr)
    if retry:
        print(tag, plan, cfg, n)
PYEOF
while read -r tag plan cfg n; do
  [ -z "$tag" ] && continue
  run_one "$tag" "$plan" "$cfg" "$n" "$tag.retry1"
done < "$RUN/retry_list.txt"
rc=0
env -u PYTHONPATH "$PY" "$D/judge_b.py" --run-dir "$RUN" --out "$RUN/verdict.json" > "$RUN/judge.stdout" 2>&1 || rc=$?
echo "$(date -u -Is) judged rc=$rc" | tee -a "$RUN/sequence.log"
OUT="$D/b_result"
mkdir -p "$OUT"
cp "$RUN/verdict.json" "$OUT/verdict.json"
cd "$REPO"
if [ "$(git branch --show-current)" = "gpu-a6000" ]; then
  before=$(git rev-parse HEAD)
  rc=0
  git add -- experiments/gpu/g10/b_result/verdict.json >> "$RUN/commit.log" 2>&1 || rc=$?
  if [ "$rc" = 0 ]; then
    git commit -m "exp(gpu): G-10 B 포화 구간 비용 비 측정과 일괄 판정 자동 commit — 기계 생성, 해석 전 (GTASK24 측정)

run dir $RUN

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>" -- \
      experiments/gpu/g10/b_result/verdict.json >> "$RUN/commit.log" 2>&1 || rc=$?
  fi
  after=$(git rev-parse HEAD)
  [ "$before" = "$after" ] && [ "$rc" = 0 ] && rc=99
  echo "$(date -u -Is) commit rc=$rc $(git rev-parse --short HEAD)" | tee -a "$RUN/sequence.log"
else
  echo "$(date -u -Is) not on gpu-a6000, no commit" | tee -a "$RUN/sequence.log"
fi
echo "$(date -u -Is) done" | tee -a "$RUN/sequence.log"
