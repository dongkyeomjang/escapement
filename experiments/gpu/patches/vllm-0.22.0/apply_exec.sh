#!/usr/bin/env bash
# Hash-guarded apply/revert of the ESCAPEMENT exec-timing layer (GTASK23, G-10 A).
#
#   bash experiments/gpu/patches/vllm-0.22.0/apply_exec.sh status|apply|revert
#
# Layered on the observation patch (apply.sh): it changes only
# vllm/v1/worker/gpu/model_runner.py, from the observation-patched content to
# the exec-layer content. The layer records CUDA events and logs [GEXEC] only
# when ESCAPEMENT_OBS=1 and ESCAPEMENT_EXEC=1; otherwise it adds one local
# assignment per step (the [GSTEP] timestamp is taken into a variable before
# the log call). Revert this layer before reverting the observation patch.
set -euo pipefail

VENV=/home/csdc/kyeom/envs/vllm-0.22.0
SP="$VENV/lib/python3.12/site-packages"
PATCH_FILE="$(cd "$(dirname "$0")" && pwd)/escapement_exec.patch"
T1="vllm/v1/core/sched/scheduler.py"
T1_PATCHED="6054015f6170e60e6f0d42cf06f1fc86d87dd9bcacaa797f15dfb523580723a1"
T2="vllm/v1/worker/gpu/model_runner.py"
T2_OBS="dc6221e92730b11538786374ce6dd8af5f75574f8d7abfcd88b07ee9ddbdcf83"
T2_EXEC="60bcc2a50aaeef0d0c96956cef5827fce501caa9ad7ee1b6f5ccff1620e3646e"

die() { echo "exec patch guard: $*" >&2; exit 1; }
sha() { sha256sum "$SP/$1" | cut -d' ' -f1; }
state() {
    [[ "$(sha "$T1")" == "$T1_PATCHED" ]] || { echo "obs-not-applied"; return; }
    case "$(sha "$T2")" in
        "$T2_OBS") echo "absent" ;;
        "$T2_EXEC") echo "present" ;;
        *) echo "drift:$(sha "$T2")" ;;
    esac
}
[[ -f "$PATCH_FILE" ]] || die "patch file not found: $PATCH_FILE"
case "${1:-}" in
    status)
        echo "$T2 $(sha "$T2")"
        echo "exec_patch_file_sha256 $(sha256sum "$PATCH_FILE" | cut -d' ' -f1)"
        echo "exec_layer: $(state)"
        ;;
    apply)
        [[ "$(state)" == "absent" ]] || die "refusing to apply, state $(state)"
        patch --forward --strip=1 --directory="$SP" --input="$PATCH_FILE" >/dev/null || die "apply failed"
        [[ "$(state)" == "present" ]] || die "post-apply sha mismatch: $(state)"
        "$VENV/bin/python" -c "import ast; ast.parse(open('$SP/$T2').read())" || die "syntax check failed"
        echo "applied. exec_layer: $(state)"
        ;;
    revert)
        [[ "$(state)" == "present" ]] || die "refusing to revert, state $(state)"
        patch --reverse --strip=1 --directory="$SP" --input="$PATCH_FILE" >/dev/null || die "revert failed"
        [[ "$(state)" == "absent" ]] || die "post-revert sha mismatch: $(state)"
        echo "reverted. exec_layer: $(state)"
        ;;
    *) echo "usage: $0 {status|apply|revert}" >&2; exit 64 ;;
esac
