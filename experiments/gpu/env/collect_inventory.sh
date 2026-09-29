#!/usr/bin/env bash
# A6000 서버 환경 inventory 수집 (read-only). GTASK01 작업 A·B4.
#
# 사용: experiments/gpu/env/collect_inventory.sh <OUT_DIR>
# OUT_DIR은 절대 경로로 넘긴다 (KNOWN_PITFALLS 1).
# GPU·driver·CUDA·package·model 파일 SHA256만 읽고 아무것도 바꾸지 않는다.
set -euo pipefail

OUT="${1:?usage: collect_inventory.sh <absolute OUT_DIR>}"
case "$OUT" in /*) ;; *) echo "OUT_DIR must be absolute: $OUT" >&2; exit 2 ;; esac
mkdir -p "$OUT"

VENV="${VENV:-/home/csdc/kyeom/envs/vllm-0.22.0}"
PY="$VENV/bin/python"
MODEL_ID="Qwen/Qwen3-4B"
MODEL_REV="1cfa9a7208912126459214e8b04321603b3df60c"
HF_HUB="${HF_HOME:-$HOME/.cache/huggingface}/hub"
SNAP="$HF_HUB/models--Qwen--Qwen3-4B/snapshots/$MODEL_REV"

{
  echo "collected_at_utc: $(date -u -Is)"
  echo "hostname: $(hostname)"
  echo "kernel: $(uname -r)"
  echo "os: $(. /etc/os-release && echo "$PRETTY_NAME")"
  echo "user: $(id -un)"
  echo "uptime: $(uptime)"
} > "$OUT/host.txt"

nvidia-smi > "$OUT/nvidia-smi.txt"
nvidia-smi -q > "$OUT/nvidia-smi-q.txt"
nvidia-smi topo -m > "$OUT/nvidia-smi-topo.txt"
nvidia-smi --query-gpu=index,name,uuid,serial,memory.total,memory.used,driver_version,persistence_mode,compute_mode,pstate \
  --format=csv > "$OUT/gpu.csv"
nvidia-smi --query-compute-apps=pid,process_name,used_memory,gpu_uuid --format=csv > "$OUT/gpu-apps.csv"
lscpu > "$OUT/lscpu.txt"
free -b > "$OUT/free.txt"
df -h / /home /mnt/nvme > "$OUT/df.txt" 2>&1 || true
ps -eo user --no-headers | sort | uniq -c > "$OUT/process-users.txt"

"$PY" --version > "$OUT/python.txt" 2>&1
uv --version >> "$OUT/python.txt" 2>&1 || true
uv pip freeze --python "$PY" > "$OUT/pip-freeze.txt"
env -u PYTHONPATH "$PY" - > "$OUT/runtime.txt" 2>&1 <<'PYEOF'
import sys, torch, vllm, transformers
print("python", sys.version.split()[0])
print("vllm", vllm.__version__, vllm.__file__)
print("torch", torch.__version__, "cuda", torch.version.cuda, "cudnn", torch.backends.cudnn.version())
print("transformers", transformers.__version__)
print("cuda_available", torch.cuda.is_available(), "device_count", torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(f"device{i}", p.name, f"cc={p.major}.{p.minor}", f"mem={p.total_memory}")
PYEOF

# model 파일 SHA256. LFS blob은 파일명이 곧 sha256이므로 두 값을 함께 기록해 대조한다.
if [ -d "$SNAP" ]; then
  {
    echo "model_id: $MODEL_ID"
    echo "revision: $MODEL_REV"
    echo "snapshot: $SNAP"
  } > "$OUT/model.txt"
  ( cd "$SNAP" && for f in $(ls -A | sort); do
      blob=$(basename "$(readlink -f "$f")")
      sum=$(sha256sum "$(readlink -f "$f")" | cut -d' ' -f1)
      size=$(stat -L -c %s "$f")
      echo "$sum  $size  $blob  $f"
    done ) > "$OUT/model-sha256.txt"
  echo "file_count: $(ls -A "$SNAP" | wc -l)" >> "$OUT/model.txt"
  echo "total_bytes: $(find -L "$SNAP" -type f -printf '%s\n' | awk '{s+=$1} END {print s}')" >> "$OUT/model.txt"
else
  echo "snapshot missing: $SNAP" > "$OUT/model.txt"
fi

echo "inventory written to $OUT"
