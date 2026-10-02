#!/usr/bin/env bash
# GTASK17 serving-condition step cost (prereg: docs/research/gpu/GPU_STEPCOST_OP_PREREG.md).
# Runs op_order.json, analyses once, then commits ONLY the two generated
# summary files to the local branch (user instruction 2026-10-01; no push).
# usage: run_stepcost_op.sh <ABS_RUN_DIR>. Do not edit while running.
set -uo pipefail
RUN="${1:?usage: run_stepcost_op.sh <abs run dir>}"
case "$RUN" in /*) ;; *) echo "run dir must be absolute" >&2; exit 2 ;; esac
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python
D="$REPO/experiments/gpu/stepcost"
mkdir -p "$RUN"
git -C "$REPO" rev-parse HEAD > "$RUN/start_commit.txt"
date -u -Is > "$RUN/start.txt"
"$PY" -c "import json;[print(x['condition'],x['rep']) for x in json.load(open('$D/op_order.json'))]" |
while read -r cond rep; do
  s=${cond:1:1}; k=${cond:3:1}; a=${cond:5:1}
  tag="${cond}.r${rep}"
  echo "$(date -u -Is) start $tag" | tee -a "$RUN/sequence.log"
  rc=0
  env -u PYTHONPATH "$PY" "$D/stepcost_op_run.py" --stream "$s" --kv "$k" --admlog "$a" --rep "$rep" \
    --out-dir "$RUN/$tag" > "$RUN/$tag.stdout" 2>&1 || rc=$?
  echo "$(date -u -Is) end $tag rc=$rc" | tee -a "$RUN/sequence.log"
done
# INVALID rule (prereg 3): rerun each invalid lifecycle once, after the sequence
"$PY" -c "import json;[print(x['condition'],x['rep']) for x in json.load(open('$D/op_order.json'))]" |
while read -r cond rep; do
  tag="${cond}.r${rep}"
  ok=$("$PY" -c "import json,sys;print(json.load(open('$RUN/$tag/summary.json'))['valid'])" 2>/dev/null || echo False)
  if [ "$ok" != "True" ]; then
    s=${cond:1:1}; k=${cond:3:1}; a=${cond:5:1}
    echo "$(date -u -Is) start $tag.retry1" | tee -a "$RUN/sequence.log"
    rc=0
    env -u PYTHONPATH "$PY" "$D/stepcost_op_run.py" --stream "$s" --kv "$k" --admlog "$a" --rep "$rep" \
      --out-dir "$RUN/$tag.retry1" > "$RUN/$tag.retry1.stdout" 2>&1 || rc=$?
    echo "$(date -u -Is) end $tag.retry1 rc=$rc" | tee -a "$RUN/sequence.log"
  fi
done
env -u PYTHONPATH "$PY" "$D/stepcost_op_analyze.py" --run-dir "$RUN" --out "$RUN/summary.json" \
  --md "$RUN/summary.md" > "$RUN/analyze.stdout" 2>&1
echo "$(date -u -Is) analyzed rc=$?" | tee -a "$RUN/sequence.log"
OUT="$D/op_result"
mkdir -p "$OUT"
# sequence.log matches .gitignore (*.log): copy it for convenience but never stage it.
# GTASK17 fix: the original `git add` listed it, add failed, `&&` skipped commit,
# and rc=$? reported the redirect, not git (commit rc=0 with HEAD unchanged).
cp "$RUN/summary.json" "$OUT/summary.json" && cp "$RUN/summary.md" "$OUT/summary.md" && \
  cp "$RUN/sequence.log" "$OUT/sequence.log"
cd "$REPO"
if [ "$(git branch --show-current)" = "gpu-a6000" ]; then
  before=$(git rev-parse HEAD)
  rc=0
  git add -- experiments/gpu/stepcost/op_result/summary.json experiments/gpu/stepcost/op_result/summary.md \
    >> "$RUN/commit.log" 2>&1 || rc=$?
  if [ "$rc" = 0 ]; then
    git commit -m "exp(gpu): 운영 조건 step 비용 측정 자동 commit — 기계 생성 요약, 해석 전 (GTASK17 측정)

run dir $RUN

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>" -- \
      experiments/gpu/stepcost/op_result/summary.json experiments/gpu/stepcost/op_result/summary.md \
      >> "$RUN/commit.log" 2>&1 || rc=$?
  fi
  after=$(git rev-parse HEAD)
  [ "$before" = "$after" ] && [ "$rc" = 0 ] && rc=99   # HEAD did not move: report as failure
  echo "$(date -u -Is) commit rc=$rc $(git rev-parse --short HEAD)" | tee -a "$RUN/sequence.log"
else
  echo "$(date -u -Is) not on gpu-a6000, no commit" | tee -a "$RUN/sequence.log"
fi
