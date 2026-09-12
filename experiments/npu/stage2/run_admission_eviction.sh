#!/usr/bin/env bash
# Admission-path eviction under back-to-back admissions (exploratory, not used
# for paper verdicts).
#
#   run_admission_eviction.sh <RUN_DIR>
#
# Requires BOTH observation patches applied: the TASK12 [BUCKET] patch and the
# TASK63 dummy-lifecycle [OBS] patch. Every repetition gets a fresh server. A
# repetition whose probe fails (saturation error) is set aside and rerun once.
# After each repetition the registered classifier decides the stop / switch
# rule: repetitions 1-5 are consecutive; if at most 2 of them are ESTABLISHED
# the mode switches to simultaneous; stop when the current mode has 5
# ESTABLISHED repetitions or after 20 repetitions.
#
# Registered in docs/research/ADMISSION_EVICTION_PLAN.md. Do not edit while a
# run is in progress (TASK23 research principle 1).
set -uo pipefail

RUN="$1"
REPO=/home/rebel/continuum-npu
cd "$REPO"

ARTIFACT="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb"
ARTIFACT_MANIFEST=b4f5cbf1634a8c4c1b0a4ca5cbda05272511007fdcbe3edb4756c3257b651f5f
CLIFF="$REPO/experiments/npu/stage2/cliff_prompts.json"
SEED=20260819
MAX_REPS=20; TARGET=5; SWITCH_AFTER=5; SWITCH_IF_AT_MOST=2

mkdir -p "$RUN/probe" "$RUN/failed" "$RUN/smi" "$RUN/class"

# Gates: both patches, the artifact, and no running server. Refuse otherwise.
bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-bucket-before.txt" 2>&1
bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh status > "$RUN/patch-dummy-before.txt" 2>&1
grep -q "state:   patched" "$RUN/patch-bucket-before.txt" || { echo "[BUCKET] patch not applied"; exit 1; }
grep -q "state:   patched" "$RUN/patch-dummy-before.txt" || { echo "[OBS] patch not applied"; exit 1; }
h=$(find "$ARTIFACT" -type f | sort | xargs sha256sum | sed "s#$ARTIFACT/##" | sha256sum | cut -d' ' -f1)
echo "artifact manifest $h expected $ARTIFACT_MANIFEST" > "$RUN/manifest.txt"
[ "$h" = "$ARTIFACT_MANIFEST" ] || { echo "artifact manifest mismatch"; exit 1; }
[ "$(pgrep -fc '[v]llm serve')" = "0" ] || { echo "a vllm server is already running"; exit 1; }
{
  echo "hostname: $(hostname)"; echo "date: $(date -Is)"; echo "git_head: $(git rev-parse HEAD)"
  for pkg in vllm vllm-rbln optimum-rbln rebel-compiler torch; do
    echo "$pkg: $(pip show "$pkg" 2>/dev/null | awk '/^Version:/{print $2}')"
  done
  sha256sum patches/vllm_rbln-0.11.1/dummy_lifecycle_observe.patch patches/vllm_rbln-0.11.1/decoder_bucket_observe.patch
} > "$RUN/provenance.txt"
rbln-smi > "$RUN/rbln-smi-before.txt" 2>&1
date -Is > "$RUN/start.txt"

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
           "$RUN/${TAG}-server-start.txt" "$RUN/${TAG}-server-stop.txt" "$RUN/smi/${TAG}.txt" \
           "$RUN/probe/admission.${TAG}.json"; do
    [ -e "$f" ] && mv "$f" "$RUN/failed/$(basename "$f").attempt1"
  done
}

run_rep() {         # $1 = TAG, $2 = MODE
  local TAG="$1" MODE="$2"
  local CMD=(experiments/npu/stage2/admission_eviction_probe.py
             --base-url http://127.0.0.1:8000 --prompts-file "$CLIFF" --mode "$MODE"
             --max-tokens 8 --seed "$SEED" --idle-s 1.0 --tag "$TAG" --output-dir "$REPO/$RUN/probe")
  echo "=== $TAG ($MODE)"
  if lifecycle "$TAG" "${CMD[@]}"; then date -Is > "$RUN/done.${TAG}"; return; fi
  echo "!!! $TAG failed; rerunning once"; set_aside "$TAG"; echo "$TAG" >> "$RUN/reruns.txt"
  if lifecycle "$TAG" "${CMD[@]}"; then date -Is > "$RUN/done.${TAG}"; else date -Is > "$RUN/invalid.${TAG}"; fi
}

mode=consecutive; est_consecutive=0; est_simultaneous=0; i=0
while [ "$i" -lt "$MAX_REPS" ]; do
  i=$((i + 1)); TAG=$(printf "R%02d" "$i")
  run_rep "$TAG" "$mode"
  if [ -f "$RUN/invalid.${TAG}" ]; then
    cls=INVALID
  else
    cls=$(env -u PYTHONPATH python3 experiments/npu/analysis/admission_eviction.py classify \
            --log "$RUN/server-${TAG}.log" --probe "$RUN/probe/admission.${TAG}.json" \
            --out "$RUN/class/${TAG}.json" 2>> "$RUN/class/${TAG}.err" | tail -1)
    [ -n "$cls" ] || cls=CLASSIFY_ERROR
  fi
  echo "$TAG $mode $cls $(date -Is)" | tee -a "$RUN/order.txt"
  if [ "$cls" = "ESTABLISHED" ]; then
    if [ "$mode" = consecutive ]; then est_consecutive=$((est_consecutive + 1)); else est_simultaneous=$((est_simultaneous + 1)); fi
  fi
  if [ "$mode" = consecutive ]; then cur=$est_consecutive; else cur=$est_simultaneous; fi
  [ "$cur" -ge "$TARGET" ] && break
  if [ "$mode" = consecutive ] && [ "$i" -eq "$SWITCH_AFTER" ] && [ "$est_consecutive" -le "$SWITCH_IF_AT_MOST" ]; then
    mode=simultaneous
    echo "switch to simultaneous after $TAG: consecutive ESTABLISHED $est_consecutive/$i $(date -Is)" | tee "$RUN/switch.txt"
  fi
done

date -Is > "$RUN/end.txt"
bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-bucket-after.txt" 2>&1
bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh status > "$RUN/patch-dummy-after.txt" 2>&1
rbln-smi > "$RUN/rbln-smi-after.txt" 2>&1
echo "finished: reps $i, consecutive ESTABLISHED $est_consecutive, simultaneous ESTABLISHED $est_simultaneous, invalid $(ls "$RUN" | grep -c '^invalid\.')"
exit 0
