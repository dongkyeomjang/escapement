#!/usr/bin/env bash
# GTASK18 context-length step cost (prereg: docs/research/gpu/GPU_STEPCOST_CTX_PREREG.md).
# Runs lifecycles r0, r1 (ctx_order.json), reruns an INVALID lifecycle once,
# analyses once, then commits ONLY the two generated summary files to the local
# gpu-a6000 branch (user instruction 2026-10-01; no push).
# usage: run_stepcost_ctx.sh <ABS_RUN_DIR>. Do not edit while running.
set -uo pipefail
RUN="${1:?usage: run_stepcost_ctx.sh <abs run dir>}"
case "$RUN" in /*) ;; *) echo "run dir must be absolute" >&2; exit 2 ;; esac
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python
D="$REPO/experiments/gpu/stepcost"
mkdir -p "$RUN"
git -C "$REPO" rev-parse HEAD > "$RUN/start_commit.txt"
date -u -Is > "$RUN/start.txt"
for rep in 0 1; do
  tag="r$rep"
  echo "$(date -u -Is) start $tag" | tee -a "$RUN/sequence.log"
  rc=0
  env -u PYTHONPATH "$PY" "$D/stepcost_ctx_run.py" --rep "$rep" --out-dir "$RUN/$tag" > "$RUN/$tag.stdout" 2>&1 || rc=$?
  echo "$(date -u -Is) end $tag rc=$rc" | tee -a "$RUN/sequence.log"
done
for rep in 0 1; do
  tag="r$rep"
  ok=$("$PY" -c "import json;print(json.load(open('$RUN/$tag/summary.json'))['valid'])" 2>/dev/null || echo False)
  if [ "$ok" != "True" ]; then
    mv "$RUN/$tag" "$RUN/$tag.invalid0"
    echo "$(date -u -Is) start $tag.retry1" | tee -a "$RUN/sequence.log"
    rc=0
    env -u PYTHONPATH "$PY" "$D/stepcost_ctx_run.py" --rep "$rep" --out-dir "$RUN/$tag.retry1" > "$RUN/$tag.retry1.stdout" 2>&1 || rc=$?
    echo "$(date -u -Is) end $tag.retry1 rc=$rc" | tee -a "$RUN/sequence.log"
  fi
done
rc=0
env -u PYTHONPATH "$PY" "$D/stepcost_ctx_analyze.py" --run-dir "$RUN" --out "$RUN/summary.json" \
  --md "$RUN/summary.md" > "$RUN/analyze.stdout" 2>&1 || rc=$?
echo "$(date -u -Is) analyzed rc=$rc" | tee -a "$RUN/sequence.log"
OUT="$D/ctx_result"
mkdir -p "$OUT"
cp "$RUN/summary.json" "$OUT/summary.json" && cp "$RUN/summary.md" "$OUT/summary.md"
cd "$REPO"
if [ "$(git branch --show-current)" = "gpu-a6000" ]; then
  before=$(git rev-parse HEAD)
  rc=0
  git add -- experiments/gpu/stepcost/ctx_result/summary.json experiments/gpu/stepcost/ctx_result/summary.md \
    >> "$RUN/commit.log" 2>&1 || rc=$?
  if [ "$rc" = 0 ]; then
    git commit -m "exp(gpu): context 길이 step 비용 측정 자동 commit — 기계 생성 요약, 해석 전 (GTASK18 측정)

run dir $RUN

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>" -- \
      experiments/gpu/stepcost/ctx_result/summary.json experiments/gpu/stepcost/ctx_result/summary.md \
      >> "$RUN/commit.log" 2>&1 || rc=$?
  fi
  after=$(git rev-parse HEAD)
  [ "$before" = "$after" ] && [ "$rc" = 0 ] && rc=99
  echo "$(date -u -Is) commit rc=$rc $(git rev-parse --short HEAD)" | tee -a "$RUN/sequence.log"
else
  echo "$(date -u -Is) not on gpu-a6000, no commit" | tee -a "$RUN/sequence.log"
fi
