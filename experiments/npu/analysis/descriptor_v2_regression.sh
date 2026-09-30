#!/usr/bin/env bash
# Regression outputs for the descriptor v2 refactor (directive 06 §4.4).
#
#   descriptor_v2_regression.sh <OUT_DIR_ABS>
#
# Runs every artifact the refactor must leave byte-identical, into OUT_DIR:
# the tables (legacy semantics), the multi-turn predictions (three predictors,
# TASK80/81), model-v0 retro R1-R5' (TASK72), the model-v1 development set
# (TASK73 A4), the model self-check and the simulator semantics effect
# (TASK74). Run once before and once after the change and compare with
# descriptor_v2_compare.py.
set -uo pipefail
OUT="$1"
case "$OUT" in /*) ;; *) echo "OUT must be absolute"; exit 64 ;; esac
REPO=/home/rebel/continuum-npu
cd "$REPO"
mkdir -p "$OUT"
A=experiments/npu/analysis
S=experiments/npu/stage3
py() { env -u PYTHONPATH python3 "$@"; }

py $A/make_tables.py --all --out-dir "$OUT/tables" > "$OUT/tables.log" 2>&1 &
py $S/predict_main.py --dp-grids $S/plans/main/DP_GRIDS.json --output "$OUT/predictions_main.json" > "$OUT/predict_main.log" 2>&1 &
py $S/predict_ext.py --output "$OUT/predictions_ext.json" > "$OUT/predict_ext.log" 2>&1 &
py $A/model_v0_retro.py --items r1,r2,r3,r4,r5p,r5 --out-dir "$OUT/model_v0_retro" > "$OUT/retro.log" 2>&1 &
py $A/model_v1_dev.py --out-dir "$OUT/model_v1_dev" > "$OUT/dev.log" 2>&1 &
py $A/model_v0_selfcheck.py --output "$OUT/selfcheck.json" > "$OUT/selfcheck.log" 2>&1 &
py $A/sim_semantics_effect.py --output "$OUT/sim_semantics.json" > "$OUT/sim_semantics.log" 2>&1 &
wait
echo "done $(date -Is)"
