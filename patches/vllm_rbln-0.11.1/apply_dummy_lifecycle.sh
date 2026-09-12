#!/usr/bin/env bash
# Hash-guarded apply/revert for the dummy-lifecycle observation patch.
#
#   sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh apply
#   sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh revert
#        bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh status   # no root needed
#
# Same guard structure as apply.sh (the TASK12 [BUCKET] patch), for a different
# file. Fail-loud: every step verifies the target's SHA256 against the recorded
# value and aborts with a non-zero exit before touching anything on mismatch.
# See DUMMY_LIFECYCLE.md for the seven policy items.
set -euo pipefail

PKG="vllm-rbln"
EXPECTED_VERSION="0.11.1"
TARGET="/usr/local/lib/python3.10/dist-packages/vllm_rbln/v1/core/prefix_cache_manager/optimum_prefix_cache_manager.py"
SHA_PRISTINE="81850a8be0ef16362db015dcc98dde71e3c902fbd48174a7e4c2a389505d296b"
SHA_PATCHED="a51f93abab815107dd762da5f9d43cd3314eb12e163c95a0b32779c11ee60856"
PATCH_FILE="$(cd "$(dirname "$0")" && pwd)/dummy_lifecycle_observe.patch"
SITE="/usr/local/lib/python3.10/dist-packages"

die() { echo "patch guard: $*" >&2; exit 1; }

current_sha() { sha256sum "$TARGET" | cut -d' ' -f1; }

check_version() {
    local v
    v="$(/usr/bin/python3 -c 'import importlib.metadata as m; print(m.version("vllm-rbln"))')"
    [[ "$v" == "$EXPECTED_VERSION" ]] || die "$PKG version drift: expected $EXPECTED_VERSION, found $v"
}

state() {
    local sha; sha="$(current_sha)"
    case "$sha" in
        "$SHA_PRISTINE") echo "pristine" ;;
        "$SHA_PATCHED")  echo "patched" ;;
        *)               echo "drift:$sha" ;;
    esac
}

[[ -f "$TARGET" ]] || die "target not found: $TARGET"
[[ -f "$PATCH_FILE" ]] || die "patch file not found: $PATCH_FILE"

case "${1:-}" in
    status)
        check_version
        echo "target:  $TARGET"
        echo "sha256:  $(current_sha)"
        echo "state:   $(state)"
        ;;
    apply)
        check_version
        s="$(state)"
        [[ "$s" != "patched" ]] || die "already patched; nothing to do"
        [[ "$s" == "pristine" ]] || die "refusing to patch, unexpected content ($s)"
        patch --forward --strip=1 --directory="$SITE" --input="$PATCH_FILE" >/dev/null \
            || die "patch application failed"
        [[ "$(current_sha)" == "$SHA_PATCHED" ]] \
            || die "post-apply sha mismatch: $(current_sha)"
        /usr/bin/python3 -c "import ast,sys; ast.parse(open('$TARGET').read())" \
            || die "post-apply syntax check failed"
        echo "applied. sha256=$(current_sha)"
        ;;
    revert)
        check_version
        s="$(state)"
        [[ "$s" != "pristine" ]] || die "already pristine; nothing to do"
        [[ "$s" == "patched" ]] || die "refusing to revert, unexpected content ($s)"
        patch --reverse --strip=1 --directory="$SITE" --input="$PATCH_FILE" >/dev/null \
            || die "patch reversal failed"
        [[ "$(current_sha)" == "$SHA_PRISTINE" ]] \
            || die "post-revert sha mismatch: $(current_sha)"
        echo "reverted. sha256=$(current_sha)"
        ;;
    *)
        echo "usage: $0 {status|apply|revert}" >&2
        exit 64
        ;;
esac
