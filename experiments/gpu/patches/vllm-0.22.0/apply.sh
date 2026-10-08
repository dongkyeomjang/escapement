#!/usr/bin/env bash
# Hash-guarded apply/revert for the ESCAPEMENT observation-only patch (GTASK03).
#
#   bash experiments/gpu/patches/vllm-0.22.0/apply.sh status
#   bash experiments/gpu/patches/vllm-0.22.0/apply.sh apply
#   bash experiments/gpu/patches/vllm-0.22.0/apply.sh revert
#
# Target: the vllm 0.22.0 install in /home/csdc/kyeom/envs/vllm-0.22.0 only
# (outside the repo, this server only). Every step checks both target files'
# SHA256 against the recorded pristine/patched values and aborts before
# touching anything on mismatch. The patch adds log lines gated by
# ESCAPEMENT_OBS=1; with the variable unset, the patched code logs nothing.
set -euo pipefail

VENV=/home/csdc/kyeom/envs/vllm-0.22.0
SP="$VENV/lib/python3.12/site-packages"
EXPECTED_VERSION="0.22.0"
PATCH_FILE="$(cd "$(dirname "$0")" && pwd)/escapement_obs.patch"

T1="vllm/v1/core/sched/scheduler.py"
T1_PRISTINE="41ff2e524c90d9aa72b72cd77492eb62ee2a729a773bd8233e970f39abbb5983"
T1_PATCHED="6054015f6170e60e6f0d42cf06f1fc86d87dd9bcacaa797f15dfb523580723a1"
T2="vllm/v1/worker/gpu/model_runner.py"
T2_PRISTINE="c5332aad7701ef66ec75747adb62b34fd542835a834808a29b7dcd6c9f688a16"
T2_PATCHED="dc6221e92730b11538786374ce6dd8af5f75574f8d7abfcd88b07ee9ddbdcf83"
# G-10 A (GTASK23): observation patch + exec-timing layer (apply_exec.sh) counts
# as patched; apply/revert of this script refuse it (revert the layer first).
T2_EXEC="60bcc2a50aaeef0d0c96956cef5827fce501caa9ad7ee1b6f5ccff1620e3646e"

die() { echo "patch guard: $*" >&2; exit 1; }
sha() { sha256sum "$SP/$1" | cut -d' ' -f1; }

one_state() {  # file pristine patched
    local s; s="$(sha "$1")"
    if [[ "$s" == "$2" ]]; then echo pristine
    elif [[ "$s" == "$3" ]]; then echo patched
    else echo "drift:$s"; fi
}

state() {
    local a b
    a="$(one_state "$T1" "$T1_PRISTINE" "$T1_PATCHED")"
    b="$(one_state "$T2" "$T2_PRISTINE" "$T2_PATCHED")"
    [[ "$b" == "drift:$T2_EXEC" && "${STATE_STRICT:-0}" != 1 ]] && b=patched
    if [[ "$a" == "$b" ]]; then echo "$a"; else echo "mixed:$T1=$a,$T2=$b"; fi
}

check_version() {
    local v
    v="$("$VENV/bin/python" -c 'import importlib.metadata as m; print(m.version("vllm"))')"
    [[ "$v" == "$EXPECTED_VERSION" ]] || die "vllm version drift: expected $EXPECTED_VERSION, found $v"
}

for t in "$T1" "$T2"; do [[ -f "$SP/$t" ]] || die "target not found: $SP/$t"; done
[[ -f "$PATCH_FILE" ]] || die "patch file not found: $PATCH_FILE"

case "${1:-}" in
    status)
        check_version
        echo "$T1 $(sha "$T1")"
        echo "$T2 $(sha "$T2")"
        echo "patch_file_sha256 $(sha256sum "$PATCH_FILE" | cut -d' ' -f1)"
        echo "state: $(state)"
        if [[ "$(sha "$T2")" == "$T2_EXEC" ]]; then echo "exec_layer: present"; else echo "exec_layer: absent"; fi
        ;;
    apply)
        check_version
        s="$(STATE_STRICT=1 state)"
        [[ "$s" != "patched" ]] || die "already patched; nothing to do"
        [[ "$s" == "pristine" ]] || die "refusing to patch, unexpected content ($s)"
        patch --forward --strip=1 --directory="$SP" --input="$PATCH_FILE" >/dev/null \
            || die "patch application failed"
        [[ "$(state)" == "patched" ]] || die "post-apply sha mismatch: $(state)"
        "$VENV/bin/python" -c "import ast; [ast.parse(open('$SP/'+f).read()) for f in ('$T1','$T2')]" \
            || die "post-apply syntax check failed"
        echo "applied. state=$(state)"
        ;;
    revert)
        check_version
        s="$(STATE_STRICT=1 state)"
        [[ "$s" != "pristine" ]] || die "already pristine; nothing to do"
        [[ "$s" == "patched" ]] || die "refusing to revert, unexpected content ($s)"
        patch --reverse --strip=1 --directory="$SP" --input="$PATCH_FILE" >/dev/null \
            || die "patch reversal failed"
        [[ "$(state)" == "pristine" ]] || die "post-revert sha mismatch: $(state)"
        echo "reverted. state=$(state)"
        ;;
    *)
        echo "usage: $0 {status|apply|revert}" >&2
        exit 64
        ;;
esac
