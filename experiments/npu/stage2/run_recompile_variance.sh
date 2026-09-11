#!/usr/bin/env bash
# Decode step cost per bucket, repeated: 3 artifacts x 5 rounds x 4 buckets.
#
#   run_recompile_variance.sh <RUN_DIR>
#
# Method is TASK13's and TASK55's: one fresh server per (artifact, bucket),
# because VLLM_RBLN_METRICS prints DECODE statistics only at shutdown,
# accumulated over the server lifetime. A "round" (회차) is one artifact's four
# buckets, each on its own lifecycle. The artifact order and the bucket order
# rotate per round; both tables are preregistered constants.
#
# Every lifecycle is checked (G1/G2 and a parsable METRICS block) as soon as it
# ends; a failed one is set aside and rerun once, immediately.
#
# Preregistered in docs/research/RECOMPILE_VARIANCE_PREREG.md. Do not edit while
# a sweep is running (TASK23 research principle 1).
set -uo pipefail

RUN="$1"
REPO=/home/rebel/continuum-npu
cd "$REPO"

PROMPT="$REPO/experiments/npu/stage1/prompt.txt"
MAX_TOKENS=512
SEED=20260819
CHECK="experiments/npu/analysis/recompile_variance.py"

declare -A ARTIFACT=(
  [A1]="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb"
  [A2]="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb6"
  [A3]="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb-rc"
)
[ -s "$RUN/manifest-A3.sha256" ] || { echo "A3 manifest missing: compile first"; exit 1; }
declare -A EXPECTED=(
  [A1]=b4f5cbf1634a8c4c1b0a4ca5cbda05272511007fdcbe3edb4756c3257b651f5f
  [A2]=348f2863eb5f8ee6b12da4ec7b73e2e7bb5227cb610fa4e610310a7032cd24bf
  [A3]="$(cat "$RUN/manifest-A3.sha256")"
)

ART_ORDERS=("A1 A2 A3" "A2 A3 A1" "A3 A1 A2" "A1 A2 A3" "A2 A3 A1")
BKT_ORDERS=("1 2 4 8" "2 4 8 1" "4 8 1 2" "8 1 2 4" "1 2 4 8")

mkdir -p "$RUN/probe" "$RUN/smi" "$RUN/failed"

ORDER_FILE="$RUN/order.txt"
: > "$ORDER_FILE"
for r in 0 1 2 3 4; do
  for a in ${ART_ORDERS[$r]}; do
    for b in ${BKT_ORDERS[$r]}; do echo "$a.r$r.L$b" >> "$ORDER_FILE"; done
  done
done
[ "$(wc -l < "$ORDER_FILE")" -eq 60 ] || { echo "order must have 60 lines"; exit 1; }

manifest_gate() {   # $1 = before|after
  local ok=0
  for a in A1 A2 A3; do
    find "${ARTIFACT[$a]}" -type f | sort | xargs sha256sum \
      | sed "s#${ARTIFACT[$a]}/##" > "$RUN/manifest-$1-$a.txt"
    local h; h=$(sha256sum < "$RUN/manifest-$1-$a.txt" | cut -d' ' -f1)
    echo "$a $h expected ${EXPECTED[$a]}" >> "$RUN/manifest-gate-$1.txt"
    [ "$h" = "${EXPECTED[$a]}" ] || ok=1
  done
  return $ok
}
: > "$RUN/manifest-gate-before.txt"
if ! manifest_gate before; then
  echo "G3 artifact identity gate failed; not starting"; cat "$RUN/manifest-gate-before.txt"; exit 1
fi

bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-before.txt" 2>&1
rbln-smi > "$RUN/rbln-smi-before.txt" 2>&1
date -Is > "$RUN/measurement-start.txt"

lifecycle() {       # $1 = TAG, returns 0 if the lifecycle passes the gates
  local TAG="$1" ART="${1%%.*}" L="${1##*.L}"
  date -Is > "$RUN/${TAG}-launch.txt"
  rbln-smi > "$RUN/smi/${TAG}.txt" 2>&1
  env -u PYTHONPATH VLLM_LOGGING_LEVEL=DEBUG VLLM_RBLN_METRICS=1 \
    vllm serve "${ARTIFACT[$ART]}" \
    --host 127.0.0.1 --port 8000 \
    > "$RUN/server-${TAG}.log" 2>&1 &
  local SRV=$! code="" i
  for i in $(seq 1 300); do
    code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null)
    [ "$code" = "200" ] && break
    kill -0 "$SRV" 2>/dev/null || break
    sleep 1
  done
  local PE=99
  if [ "$code" = "200" ]; then
    date -Is > "$RUN/${TAG}-server-start.txt"
    env -u PYTHONPATH "$REPO/experiments/npu/launch/run_isolated_python.sh" \
      experiments/npu/stage2/decode_cost_probe.py \
      --base-url http://127.0.0.1:8000 \
      --prompt-file "$PROMPT" \
      --level "$L" --max-tokens "$MAX_TOKENS" --seed "$SEED" \
      --output-dir "$REPO/$RUN/probe" > "$RUN/probe-${TAG}.log" 2>&1
    PE=$?
  else
    echo "!!! $TAG: server never became healthy"
  fi
  # METRICS are printed on shutdown. Terminate by our own pid, never by pattern.
  kill -TERM "$SRV" 2>/dev/null
  for i in $(seq 1 60); do kill -0 "$SRV" 2>/dev/null || break; sleep 1; done
  if kill -0 "$SRV" 2>/dev/null; then
    kill -KILL "$SRV" 2>/dev/null; sleep 5; echo "$TAG: server needed SIGKILL"
  fi
  wait "$SRV" 2>/dev/null
  date -Is > "$RUN/${TAG}-server-stop.txt"
  mv "$RUN/probe/decode_cost.level${L}.json" "$RUN/probe/decode_cost.${TAG}.json" 2>/dev/null
  [ "$PE" -eq 0 ] || return 1
  env -u PYTHONPATH python3 "$CHECK" check \
    --log "$RUN/server-${TAG}.log" --probe "$RUN/probe/decode_cost.${TAG}.json" \
    --level "$L" > "$RUN/check-${TAG}.json" 2>&1
}

set_aside() {       # keep a failed attempt's files under failed/
  local TAG="$1" f
  for f in "$RUN/server-${TAG}.log" "$RUN/probe-${TAG}.log" "$RUN/check-${TAG}.json" \
           "$RUN/probe/decode_cost.${TAG}.json" "$RUN/${TAG}-launch.txt" \
           "$RUN/${TAG}-server-start.txt" "$RUN/${TAG}-server-stop.txt" \
           "$RUN/smi/${TAG}.txt"; do
    [ -e "$f" ] && mv "$f" "$RUN/failed/$(basename "$f").attempt1"
  done
}

invalid=0
while read -r TAG; do
  [ -f "$RUN/done.${TAG}" ] && { echo "$TAG already done, skipping"; continue; }
  echo "=== $TAG"
  if lifecycle "$TAG"; then
    date -Is > "$RUN/done.${TAG}"
  else
    echo "!!! $TAG failed its gates; rerunning once"
    set_aside "$TAG"
    echo "$TAG" >> "$RUN/reruns.txt"
    if lifecycle "$TAG"; then
      date -Is > "$RUN/done.${TAG}"
    else
      echo "!!! $TAG INVALID after rerun"
      date -Is > "$RUN/invalid.${TAG}"
      invalid=$((invalid + 1))
    fi
  fi
done < "$ORDER_FILE"

date -Is > "$RUN/measurement-end.txt"
: > "$RUN/manifest-gate-after.txt"
manifest_gate after || echo "G3 after-measurement identity check FAILED"
bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-after.txt" 2>&1
rbln-smi > "$RUN/rbln-smi-after.txt" 2>&1
df -h / | tail -1 > "$RUN/disk-after.txt"
echo "invalid lifecycles: $invalid"
date -Is > "$RUN/driver-finished.txt"
exit 0
