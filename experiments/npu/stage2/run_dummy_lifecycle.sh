#!/usr/bin/env bash
# Dummy-block lifecycle observation (exploratory, not used for paper verdicts).
#
#   run_dummy_lifecycle.sh <RUN_DIR> pilot   # log-volume check, 1 lifecycle
#   run_dummy_lifecycle.sh <RUN_DIR> main    # experiments A (8) and B (2)
#
# Requires BOTH observation patches applied: the TASK12 [BUCKET] patch and the
# dummy-lifecycle [OBS] patch. Every trial gets a fresh server, because the
# outer-block pool does not reset without a restart. A failed trial is set
# aside and rerun once, immediately.
#
# Registered in docs/research/DUMMY_LIFECYCLE_PLAN.md. Do not edit while a run
# is in progress (TASK23 research principle 1).
set -uo pipefail

RUN="$1"; PHASE="$2"
REPO=/home/rebel/continuum-npu
cd "$REPO"

ARTIFACT="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb"
ARTIFACT_MANIFEST=b4f5cbf1634a8c4c1b0a4ca5cbda05272511007fdcbe3edb4756c3257b651f5f
PROMPT="$REPO/experiments/npu/stage1/prompt.txt"
CLIFF="$REPO/experiments/npu/stage2/cliff_prompts.json"
SEED=20260819

mkdir -p "$RUN/probe" "$RUN/failed" "$RUN/smi"

# Gates: both patches, the artifact, and a free port. Refuse to start otherwise.
bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-bucket-$PHASE-before.txt" 2>&1
bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh status > "$RUN/patch-dummy-$PHASE-before.txt" 2>&1
grep -q "state:   patched" "$RUN/patch-bucket-$PHASE-before.txt" || { echo "[BUCKET] patch not applied"; exit 1; }
grep -q "state:   patched" "$RUN/patch-dummy-$PHASE-before.txt" || { echo "[OBS] patch not applied"; exit 1; }
h=$(find "$ARTIFACT" -type f | sort | xargs sha256sum | sed "s#$ARTIFACT/##" | sha256sum | cut -d' ' -f1)
echo "artifact manifest $h expected $ARTIFACT_MANIFEST" > "$RUN/manifest-$PHASE.txt"
[ "$h" = "$ARTIFACT_MANIFEST" ] || { echo "artifact manifest mismatch"; exit 1; }
[ "$(pgrep -fc '[v]llm serve')" = "0" ] || { echo "a vllm server is already running"; exit 1; }
rbln-smi > "$RUN/rbln-smi-$PHASE-before.txt" 2>&1
date -Is > "$RUN/$PHASE-start.txt"

lifecycle() {       # $1 = TAG, $2... = probe command; returns probe exit code
  local TAG="$1"; shift
  date -Is > "$RUN/${TAG}-launch.txt"
  rbln-smi > "$RUN/smi/${TAG}.txt" 2>&1
  env -u PYTHONPATH VLLM_LOGGING_LEVEL=DEBUG VLLM_RBLN_METRICS=1 \
    vllm serve "$ARTIFACT" --host 127.0.0.1 --port 8000 --enable-prefix-caching \
    > "$RUN/server-${TAG}.log" 2>&1 &
  local SRV=$! code="" i PE=99
  for i in $(seq 1 300); do
    code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null)
    [ "$code" = "200" ] && break
    kill -0 "$SRV" 2>/dev/null || break
    sleep 1
  done
  if [ "$code" = "200" ]; then
    date -Is > "$RUN/${TAG}-server-start.txt"
    env -u PYTHONPATH "$REPO/experiments/npu/launch/run_isolated_python.sh" "$@" \
      > "$RUN/probe-${TAG}.log" 2>&1
    PE=$?
  else
    echo "!!! $TAG: server never became healthy"
  fi
  kill -TERM "$SRV" 2>/dev/null
  for i in $(seq 1 60); do kill -0 "$SRV" 2>/dev/null || break; sleep 1; done
  if kill -0 "$SRV" 2>/dev/null; then
    kill -KILL "$SRV" 2>/dev/null; sleep 5; echo "$TAG: server needed SIGKILL"
  fi
  wait "$SRV" 2>/dev/null
  date -Is > "$RUN/${TAG}-server-stop.txt"
  return $PE
}

set_aside() {
  local TAG="$1" f
  for f in "$RUN/server-${TAG}.log" "$RUN/probe-${TAG}.log" "$RUN/${TAG}-launch.txt" \
           "$RUN/${TAG}-server-start.txt" "$RUN/${TAG}-server-stop.txt" "$RUN/smi/${TAG}.txt"; do
    [ -e "$f" ] && mv "$f" "$RUN/failed/$(basename "$f").attempt1"
  done
}

run_trial() {       # $1 = TAG, rest = probe command
  local TAG="$1"
  [ -f "$RUN/done.${TAG}" ] && { echo "$TAG already done"; return; }
  echo "=== $TAG"
  if lifecycle "$@"; then date -Is > "$RUN/done.${TAG}"; return; fi
  echo "!!! $TAG failed; rerunning once"; set_aside "$TAG"; echo "$TAG" >> "$RUN/reruns.txt"
  if lifecycle "$@"; then date -Is > "$RUN/done.${TAG}"; else date -Is > "$RUN/invalid.${TAG}"; fi
}

case "$PHASE" in
  pilot)
    run_trial pilot experiments/npu/stage2/decode_cost_probe.py \
      --base-url http://127.0.0.1:8000 --prompt-file "$PROMPT" \
      --level 1 --max-tokens 512 --seed "$SEED" --output-dir "$REPO/$RUN/probe"
    ;;
  main)
    for K in B5r0 B5r1 B6r0 B6r1 B7r0 B7r1 B8r0 B8r1; do
      run_trial "A.$K" experiments/npu/stage2/gap_turnover_probe.py \
        --base-url http://127.0.0.1:8000 --prompts-file "$CLIFF" \
        --trial "$K" --max-tokens 8 --seed "$SEED" --output-dir "$REPO/$RUN/probe"
    done
    for T in b0 b1; do
      run_trial "B.$T" experiments/npu/stage2/dummy_lifecycle_b_probe.py \
        --base-url http://127.0.0.1:8000 --prompt-file "$PROMPT" \
        --n 8 --spacing-s 0.3 --max-tokens 384 --seed "$SEED" \
        --tag "$T" --output-dir "$REPO/$RUN/probe"
    done
    ;;
  *) echo "usage: $0 <RUN> pilot|main"; exit 64 ;;
esac

date -Is > "$RUN/$PHASE-end.txt"
bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-bucket-$PHASE-after.txt" 2>&1
bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh status > "$RUN/patch-dummy-$PHASE-after.txt" 2>&1
rbln-smi > "$RUN/rbln-smi-$PHASE-after.txt" 2>&1
echo "phase $PHASE finished; invalid: $(ls "$RUN" | grep -c '^invalid\.')"
exit 0
