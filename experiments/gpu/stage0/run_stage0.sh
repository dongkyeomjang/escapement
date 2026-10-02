#!/usr/bin/env bash
# GPU Stage 0 serving lifecycle (GTASK02). One call = one server lifecycle.
#
# 사용: experiments/gpu/stage0/run_stage0.sh <ABS_RUN_DIR> <L1|L2|L3>
#   L1: 기본값 해석 확인 (override 없음)
#   L2: PASS 판정 lifecycle (--block-size 16, --num-gpu-blocks-override 2048,
#       cudagraph_capture_sizes [1,2,4,6,8], --cudagraph-metrics)
#   L3: L2 + VLLM_USE_V2_MODEL_RUNNER=0 (탐색, 판정 없음)
#
# 규칙 (KNOWN_PITFALLS): 경로는 절대 경로, server는 받은 PID로만 종료,
# 실행 중 이 파일을 편집하지 않는다.
set -euo pipefail

RUN="${1:?usage: run_stage0.sh <abs run dir> <L1|L2|L3>}"
LC="${2:?usage: run_stage0.sh <abs run dir> <L1|L2|L3>}"
case "$RUN" in /*) ;; *) echo "run dir must be absolute" >&2; exit 2 ;; esac

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VENV=/home/csdc/kyeom/envs/vllm-0.22.0
PORT=8100
GPU=0
REV=1cfa9a7208912126459214e8b04321603b3df60c
OUT="$RUN/$LC"
mkdir -p "$OUT"

export CUDA_VISIBLE_DEVICES=$GPU
export HF_HOME=/mnt/nvme/hf
export HF_HUB_OFFLINE=1
export HF_HUB_ENABLE_HF_TRANSFER=0
unset PYTHONPATH

ARGS=(
  serve Qwen/Qwen3-4B
  --revision "$REV"
  --dtype bfloat16
  --max-model-len 8192
  --max-num-seqs 8
  --seed 20260929
  --host 127.0.0.1 --port "$PORT"
  --generation-config vllm
  --enable-prompt-tokens-details
)
EXTRA_ENV=()
case "$LC" in
  L1) ;;
  L2|L3)
    ARGS+=(
      --block-size 16
      --num-gpu-blocks-override 2048
      --compilation-config '{"cudagraph_capture_sizes": [1, 2, 4, 6, 8]}'
      --cudagraph-metrics
    )
    ;;
  *) echo "unknown lifecycle $LC" >&2; exit 2 ;;
esac
if [ "$LC" = L3 ]; then
  export VLLM_USE_V2_MODEL_RUNNER=0
  EXTRA_ENV+=(VLLM_USE_V2_MODEL_RUNNER=0)
fi

# provenance
{
  echo "lifecycle: $LC"
  echo "start_utc: $(date -u -Is)"
  echo "repo_head: $(git -C "$REPO" rev-parse HEAD)"
  echo "repo_branch: $(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
  echo "repo_dirty: $(git -C "$REPO" status --porcelain | wc -l) entries"
  echo "vllm: $("$VENV/bin/python" -c 'import vllm; print(vllm.__version__)')"
  echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES HF_HOME=$HF_HOME HF_HUB_OFFLINE=$HF_HUB_OFFLINE ${EXTRA_ENV[*]:-}"
  printf 'command: %q ' "$VENV/bin/vllm" "${ARGS[@]}"; echo
} > "$OUT/provenance.txt"
env | sort > "$OUT/env.txt"
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv > "$OUT/nvidia-smi-pre.csv"
nvidia-smi --query-compute-apps=pid,process_name,used_memory,gpu_uuid --format=csv > "$OUT/gpu-apps-pre.csv"

if curl -s -o /dev/null "http://127.0.0.1:$PORT/health"; then
  echo "port $PORT already serving; refusing to start" >&2; exit 3
fi

"$VENV/bin/vllm" "${ARGS[@]}" > "$OUT/server.log" 2>&1 &
SRV=$!
echo "server_pid: $SRV" >> "$OUT/provenance.txt"

cleanup() {
  if kill -0 "$SRV" 2>/dev/null; then
    kill -TERM "$SRV" 2>/dev/null || true
    for _ in $(seq 1 60); do kill -0 "$SRV" 2>/dev/null || break; sleep 1; done
    kill -KILL "$SRV" 2>/dev/null || true
  fi
  wait "$SRV" 2>/dev/null || true
  echo "stop_utc: $(date -u -Is)" >> "$OUT/provenance.txt"
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv > "$OUT/nvidia-smi-post.csv"
}
trap cleanup EXIT

ready=0
for _ in $(seq 1 900); do
  if ! kill -0 "$SRV" 2>/dev/null; then echo "server exited during startup" >&2; exit 4; fi
  if curl -sf -o /dev/null "http://127.0.0.1:$PORT/health"; then ready=1; break; fi
  sleep 1
done
[ "$ready" = 1 ] || { echo "server not ready after 900 s" >&2; exit 5; }
echo "ready_utc: $(date -u -Is)" >> "$OUT/provenance.txt"

nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv > "$OUT/nvidia-smi-ready.csv"
nvidia-smi --query-compute-apps=pid,process_name,used_memory,gpu_uuid --format=csv > "$OUT/gpu-apps-ready.csv"

PROBE_ARGS=(--base "http://127.0.0.1:$PORT" --out-dir "$OUT/probe")
[ "$LC" = L1 ] || PROBE_ARGS+=(--concurrency-block)
rc=0
"$VENV/bin/python" "$REPO/experiments/gpu/stage0/probe.py" "${PROBE_ARGS[@]}" > "$OUT/probe.stdout" 2>&1 || rc=$?
echo "probe_exit: $rc" >> "$OUT/provenance.txt"
