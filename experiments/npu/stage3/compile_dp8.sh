#!/usr/bin/env bash
# Compile the N = 8 DP grid (1,2,3,4,6,16), batch 16, once (directive 05 §3).
#
#   compile_dp8.sh <RUN_DIR_ABS>
#
# The command is TASK34's TUNED compile word for word except the decoder
# widths and the output directory; HF_HUB_OFFLINE=1 pins the weights to the
# cached snapshot as in TASK62. One attempt only: a failure is reported, not
# retried. An existing output directory is never overwritten.
set -uo pipefail

RUN="$1"
REPO=/home/rebel/continuum-npu
case "$RUN" in /*) ;; *) echo "RUN must be absolute"; exit 64 ;; esac
cd "$REPO"

OUT="$REPO/models/Qwen3-4B-rbln-b16-s8192-d4-dp8"
TUNED="$REPO/models/Qwen3-4B-rbln-b16-s8192-d4-mb16"
C="$RUN/compile"

if [ -e "$OUT" ]; then echo "refusing: $OUT already exists"; exit 2; fi
mkdir -p "$C"

bash patches/vllm_rbln-0.11.1/apply.sh status > "$C/patch-state.txt" 2>&1
rbln-stat > "$C/rbln-stat-before.txt" 2>&1
python3 -m pip freeze > "$C/pip-freeze.txt" 2>&1
env | grep -E '^(RBLN|HF_|VLLM|PYTHON|TRANSFORMERS|TORCH|OMP|MKL)' | sort > "$C/env-before.txt"
{ hostname; uname -r; } > "$C/host.txt"
ls ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/ > "$C/hf-snapshots.txt"
df -h / | tail -1 > "$C/df-before.txt"
du -sh models > "$C/du-models-before.txt"
git rev-parse HEAD > "$C/git-head.txt"

date -Is > "$C/started_at.txt"
env -u PYTHONPATH HF_HUB_OFFLINE=1 /usr/bin/time -v timeout 1800 optimum-rbln-cli \
  --model-id Qwen/Qwen3-4B \
  --output-dir "$OUT" \
  --batch_size 16 --decoder_batch_sizes 1,2,3,4,6,16 \
  --max_seq_len 8192 --num_devices 4 > "$C/compile.log" 2>&1
echo $? > "$C/exit_code.txt"
date -Is > "$C/finished_at.txt"

df -h / | tail -1 > "$C/df-after.txt"
du -sh models > "$C/du-models-after.txt"
rbln-stat > "$C/rbln-stat-after.txt" 2>&1
ls ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/ > "$C/hf-snapshots-after.txt"

if [ "$(cat "$C/exit_code.txt")" != "0" ]; then
  echo "compile failed (exit $(cat "$C/exit_code.txt")); not retrying"; exit 1
fi

cp "$OUT/rbln_config.json" "$C/rbln_config-dp8.json"
diff "$TUNED/rbln_config.json" "$C/rbln_config-dp8.json" > "$C/rbln_config-diff-vs-TUNED.txt"
find "$OUT" -type f | sort | xargs sha256sum | sed "s#$OUT/##" > "$C/manifest-dp8.txt"
sha256sum < "$C/manifest-dp8.txt" | cut -d' ' -f1 > "$C/manifest-dp8.sha256"
find "$OUT" -type f -printf '%s %P\n' | sort -k2 > "$C/sizes-dp8.txt"
du -sb "$OUT" > "$C/du-dp8.txt"
echo "dp8 manifest $(cat "$C/manifest-dp8.sha256")"
