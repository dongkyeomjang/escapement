#!/usr/bin/env bash
# Recompile the (1,2,4,8) / batch 8 artifact once, the same way TASK10 did.
#
#   compile_recompile_a3.sh <RUN_DIR>
#
# The command is TASK10's, word for word, except for the output directory and
# HF_HUB_OFFLINE=1. The offline flag pins the weights to the one cached
# snapshot (TASK06 revision 1cfa9a72...) and makes an unapproved download
# impossible; it is the one known environment difference from TASK10 and is
# recorded as such. One attempt only: a failure is reported, not retried.
#
# Preregistered in docs/research/RECOMPILE_VARIANCE_PREREG.md.
set -uo pipefail

RUN="$1"
REPO=/home/rebel/continuum-npu
cd "$REPO"

A1="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb"
OUT="$REPO/models/Qwen3-4B-rbln-b8-s8192-d4-mb-rc"
A1_COMPILE="$REPO/results/npu/stage1/20260819-174300-stage1b-b8-multibucket/compile"
C="$RUN/compile"

if [ -e "$OUT" ]; then echo "refusing: $OUT already exists"; exit 2; fi
mkdir -p "$C"

bash patches/vllm_rbln-0.11.1/apply.sh status > "$C/patch-state.txt" 2>&1
rbln-smi > "$C/rbln-smi-before.txt" 2>&1
python3 -m pip freeze > "$C/pip-freeze.txt" 2>&1
env | grep -E '^(RBLN|HF_|VLLM|PYTHON|TRANSFORMERS|TORCH|OMP|MKL)' | sort > "$C/env-before.txt"
{ hostname; uname -r; } > "$C/host.txt"
ls ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/ > "$C/hf-snapshots.txt"
df -h / | tail -1 > "$C/df-before.txt"
du -sh models > "$C/du-models-before.txt"

date -Is > "$C/started_at.txt"
env -u PYTHONPATH HF_HUB_OFFLINE=1 /usr/bin/time -v timeout 1800 optimum-rbln-cli \
  --model-id Qwen/Qwen3-4B \
  --output-dir "$OUT" \
  --batch_size 8 --decoder_batch_sizes 1,2,4,8 \
  --max_seq_len 8192 --num_devices 4 > "$C/compile.log" 2>&1
echo $? > "$C/exit_code.txt"
date -Is > "$C/finished_at.txt"

df -h / | tail -1 > "$C/df-after.txt"
du -sh models > "$C/du-models-after.txt"
rbln-smi > "$C/rbln-smi-after.txt" 2>&1
ls ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/ > "$C/hf-snapshots-after.txt"

if [ "$(cat "$C/exit_code.txt")" != "0" ]; then
  echo "compile failed (exit $(cat "$C/exit_code.txt")); not retrying"; exit 1
fi

cp "$OUT/rbln_config.json" "$C/rbln_config-rc.json"
diff "$A1_COMPILE/rbln_config-b8.json" "$C/rbln_config-rc.json" > "$C/rbln_config-diff-vs-A1-compile-record.txt"
diff "$A1/rbln_config.json" "$C/rbln_config-rc.json" > "$C/rbln_config-diff-vs-A1-artifact.txt"

# Manifest in the same form as run_step_cost.sh, so the identity gate of the
# measurement driver can compare it byte for byte.
find "$OUT" -type f | sort | xargs sha256sum | sed "s#$OUT/##" > "$RUN/manifest-A3.txt"
sha256sum < "$RUN/manifest-A3.txt" | cut -d' ' -f1 > "$RUN/manifest-A3.sha256"
find "$A1" -type f | sort | xargs sha256sum | sed "s#$A1/##" > "$C/manifest-A1.txt"
join -j 2 <(awk '{print $1, $2}' "$C/manifest-A1.txt" | sort -k2) \
          <(awk '{print $1, $2}' "$RUN/manifest-A3.txt" | sort -k2) \
  | awk '{print $1, ($2 == $3 ? "same" : "DIFFERENT")}' > "$C/bytes-vs-A1.txt"
find "$OUT" -type f -printf '%s %P\n' | sort -k2 > "$C/sizes-A3.txt"
find "$A1" -type f -printf '%s %P\n' | sort -k2 > "$C/sizes-A1.txt"
echo "A3 manifest $(cat "$RUN/manifest-A3.sha256")"
cat "$C/bytes-vs-A1.txt"
