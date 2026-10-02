#!/usr/bin/env bash
# G-07 C blind cells N = 25, 28 (prereg docs/research/gpu/GPU_BLIND_COLLAPSE_PREREG.md).
# 1. plans/blind/ORDER.json via run_schedule.py; 2. every lifecycle that is
# INVALID (runner or measurement checks) once more as <tag>.retry1, after the
# order; 3. blind_judge.py once; 4. commit ONLY blind_result/verdict.json to
# the local gpu-a6000 branch (user instruction 2026-10-01; no push).
# usage: run_blind.sh <ABS_RUN_DIR>. Do not edit the scripts while it runs.
set -uo pipefail
RUN="${1:?usage: run_blind.sh <abs run dir>}"
case "$RUN" in /*) ;; *) echo "run dir must be absolute" >&2; exit 2 ;; esac
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python
D="$REPO/experiments/gpu/multiturn"
mkdir -p "$RUN"
git -C "$REPO" rev-parse HEAD > "$RUN/start_commit.txt"
date -u -Is > "$RUN/start.txt"
"$PY" "$D/run_schedule.py" --schedule "$D/plans/blind/ORDER.json" --run-dir "$RUN" >> "$RUN/driver.log" 2>&1
# INVALID rerun (GTASK11 amendment 1 7.5): once, same plan, after the order
env -u PYTHONPATH "$PY" - "$RUN" "$D" <<'PYEOF' > "$RUN/retry_list.txt" 2>> "$RUN/driver.log"
import json, sys
from pathlib import Path
run, d = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(d))
import gpu_mt_measure as M
for e in json.loads((d / "plans/blind/ORDER.json").read_text()):
    p = run / e["tag"]
    ok = False
    if (p / "windows.json").exists():
        try:
            ok = M.lifecycle_metrics(p)["valid"]
        except Exception as ex:  # a broken lifecycle is INVALID
            print(f"# {e['tag']} metrics error {ex!r}", file=sys.stderr)
    if not ok:
        print(e["tag"], e["plan"], e["config"], e["n"])
PYEOF
while read -r tag plan cfg n; do
  [ -z "$tag" ] && continue
  echo "$(date -u -Is) start $tag.retry1" | tee -a "$RUN/sequence.log"
  rc=0
  "$PY" "$D/gpu_mt_runner.py" --plan "$plan" --config "$cfg" --n "$n" --out-dir "$RUN/$tag.retry1" --stream \
    > "$RUN/$tag.retry1.stdout" 2>&1 || rc=$?
  echo "$(date -u -Is) end $tag.retry1 rc=$rc" | tee -a "$RUN/sequence.log"
done < "$RUN/retry_list.txt"
rc=0
env -u PYTHONPATH "$PY" "$D/blind_judge.py" --run-dir "$RUN" --out "$RUN/verdict.json" > "$RUN/judge.stdout" 2>&1 || rc=$?
echo "$(date -u -Is) judged rc=$rc" | tee -a "$RUN/sequence.log"
OUT="$D/blind_result"
mkdir -p "$OUT"
cp "$RUN/verdict.json" "$OUT/verdict.json"
cd "$REPO"
if [ "$(git branch --show-current)" = "gpu-a6000" ]; then
  before=$(git rev-parse HEAD)
  rc=0
  git add -- experiments/gpu/multiturn/blind_result/verdict.json >> "$RUN/commit.log" 2>&1 || rc=$?
  if [ "$rc" = 0 ]; then
    git commit -m "exp(gpu): 붕괴 영역 blind N=25·28 측정과 일괄 판정 자동 commit — 기계 생성, 해석 전 (GTASK20 측정)

run dir $RUN

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>" -- \
      experiments/gpu/multiturn/blind_result/verdict.json >> "$RUN/commit.log" 2>&1 || rc=$?
  fi
  after=$(git rev-parse HEAD)
  [ "$before" = "$after" ] && [ "$rc" = 0 ] && rc=99
  echo "$(date -u -Is) commit rc=$rc $(git rev-parse --short HEAD)" | tee -a "$RUN/sequence.log"
else
  echo "$(date -u -Is) not on gpu-a6000, no commit" | tee -a "$RUN/sequence.log"
fi
