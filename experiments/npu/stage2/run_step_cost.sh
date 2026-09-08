#!/usr/bin/env bash
# TASK55 driver: decode step cost per compiled bucket, on both grids.
#
#   run_step_cost.sh <RUN_DIR>
#
# Same method as TASK13: one dedicated server per concurrency level, because
# VLLM_RBLN_METRICS prints its DECODE statistics only at shutdown, accumulated
# over the whole server lifetime. Only the artifact and the level set change.
#
# Preregistered in docs/research/GRID_STEP_COST_PREREG.md. Do not edit while a
# sweep is running (TASK23 research principle 1).
set -uo pipefail

RUN="$1"
REPO=/home/rebel/continuum-npu
cd "$REPO"

ORDER_SEED=20260955
PROMPT="$REPO/experiments/npu/stage1/prompt.txt"
MAX_TOKENS=512
SEED=20260819

declare -A ARTIFACT=(
  [mb]="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb"
  [mb6]="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb6"
)

mkdir -p "$RUN/probe"

# The order is a preregistered constant, but recompute it from the same
# function rather than pasting it in, so script and document cannot drift.
ORDER_FILE="$RUN/order.txt"
env -u PYTHONPATH PYTHONPATH="$REPO/src" python3 - "$ORDER_SEED" > "$ORDER_FILE" <<'PY'
import sys
from continuum.workload.paired import balanced_arm_orders
cfgs = [f"{a}.L{l}" for a, ls in (("mb", (1, 2, 4, 8)), ("mb6", (1, 2, 4, 6, 8)))
        for l in ls]
for cfg in balanced_arm_orders(cfgs, rounds=1, base_seed=int(sys.argv[1]),
                               block_id="task55-order")[0]:
    print(cfg)
PY
[ -s "$ORDER_FILE" ] || { echo "order generation failed"; exit 1; }

# Artifact identity gate: these must be the same two artifacts TASK54 used.
for g in mb mb6; do
  find "${ARTIFACT[$g]}" -type f | sort | xargs sha256sum \
    | sed "s#${ARTIFACT[$g]}/##" > "$RUN/manifest-$g.txt"
  sha256sum < "$RUN/manifest-$g.txt" | cut -d' ' -f1 > "$RUN/manifest-$g.sha256"
  echo "$g manifest $(cat "$RUN/manifest-$g.sha256")"
done

bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-before.txt" 2>&1
rbln-smi > "$RUN/rbln-smi-before.txt" 2>&1
date -Is > "$RUN/measurement-start.txt"

fail=0
while read -r CFG; do
  GRID="${CFG%%.*}"; L="${CFG#*.L}"
  TAG="${GRID}.L${L}"
  DONE_MARK="$RUN/done.${TAG}"
  if [ -f "$DONE_MARK" ]; then echo "$TAG already done, skipping"; continue; fi

  echo "=== $TAG"
  env -u PYTHONPATH VLLM_LOGGING_LEVEL=DEBUG VLLM_RBLN_METRICS=1 \
    vllm serve "${ARTIFACT[$GRID]}" \
    --host 127.0.0.1 --port 8000 \
    > "$RUN/server-${TAG}.log" 2>&1 &
  SRV=$!

  code=""
  for i in $(seq 1 300); do
    code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null)
    [ "$code" = "200" ] && break
    kill -0 "$SRV" 2>/dev/null || break
    sleep 1
  done
  if [ "$code" != "200" ]; then
    echo "!!! $TAG: server never became healthy"
    kill -TERM "$SRV" 2>/dev/null; wait "$SRV" 2>/dev/null
    fail=$((fail + 1)); continue
  fi

  date -Is > "$RUN/${TAG}-server-start.txt"
  env -u PYTHONPATH "$REPO/experiments/npu/launch/run_isolated_python.sh" \
    experiments/npu/stage2/decode_cost_probe.py \
    --base-url http://127.0.0.1:8000 \
    --prompt-file "$PROMPT" \
    --level "$L" --max-tokens "$MAX_TOKENS" --seed "$SEED" \
    --output-dir "$REPO/$RUN/probe" > "$RUN/probe-${TAG}.log" 2>&1
  PE=$?

  # The METRICS block is printed on shutdown, so the log is only complete
  # after this server is gone. Terminate by our own pid, never by pattern.
  kill -TERM "$SRV" 2>/dev/null
  for i in $(seq 1 60); do kill -0 "$SRV" 2>/dev/null || break; sleep 1; done
  if kill -0 "$SRV" 2>/dev/null; then
    kill -KILL "$SRV" 2>/dev/null; sleep 5; echo "$TAG: server needed SIGKILL"
  fi
  wait "$SRV" 2>/dev/null
  date -Is > "$RUN/${TAG}-server-stop.txt"

  # decode_cost_probe names its output by level alone; both grids share the
  # level set, so tag the file before the next grid overwrites it.
  mv "$RUN/probe/decode_cost.level${L}.json" \
     "$RUN/probe/decode_cost.${TAG}.json" 2>/dev/null

  if [ "$PE" -eq 0 ] && [ -f "$RUN/probe/decode_cost.${TAG}.json" ]; then
    date -Is > "$DONE_MARK"
  else
    echo "!!! $TAG: probe exit $PE"
    fail=$((fail + 1))
  fi
  echo "$TAG done (probe exit $PE)"
done < "$ORDER_FILE"

date -Is > "$RUN/measurement-end.txt"
bash patches/vllm_rbln-0.11.1/apply.sh status > "$RUN/patch-after.txt" 2>&1
rbln-smi > "$RUN/rbln-smi-after.txt" 2>&1
df -h / | tail -1 > "$RUN/disk-after.txt"

echo "levels with a problem: $fail"
exit 0
