#!/bin/bash

# ============================================================================
# Stop the Flutter SDK misreading YOUR repository as itself inside git hooks.
#
# `git commit` / `git push` export GIT_DIR (and GIT_WORK_TREE,
# GIT_INDEX_FILE) to every hook they run. The flutter tool shells out to git
# to identify its own SDK, and `git -C "$FLUTTER_ROOT" rev-parse HEAD`
# (bin/internal/shared.sh) does NOT beat an inherited GIT_DIR -- `-C` only
# changes directory, while GIT_DIR overrides repository discovery outright:
#
#     $ git -C /opt/flutter rev-parse HEAD
#     058e0af2c2...                                  <- Flutter's HEAD
#     $ GIT_DIR=~/some-repo/.git git -C /opt/flutter rev-parse HEAD
#     84bd550331...                                  <- YOUR repo's HEAD
#
# So inside a hook, `flutter --version` reports your project as the SDK, pub
# resolves the SDK as "0.0.0-unknown" and every version constraint becomes
# unsatisfiable ("... is forbidden"). Worse, flutter caches that answer in
# bin/cache/flutter.version.json, so the corruption outlives the hook and
# follows the next caller into an unrelated repository -- which is why the
# same command passes when you re-run it by hand and fails again next push.
#
# Upstream already unsets these variables in bin/internal/content_aware_hash.sh
# and bin/internal/update_engine_version.sh, but not in the version path.
#
# THE FIX: a wrapper ahead of /usr/bin on PATH that strips the git-hook
# variables and hands off to the real binary. Per-call `env -u GIT_DIR ...` in
# each hook works too, but only for as long as every future hook author
# remembers; this makes the failure impossible for every caller in every repo.
#
# Deliberately NOT patching /opt/flutter/bin/internal/shared.sh: that file is
# owned by the flutter-bin package and the next update would silently restore
# the bug.
#
# Usage: fix_flutter_git_env.sh [--check | --uninstall]
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly BIN_DIR="${HOME}/.local/bin"
readonly LIB_DIR="${HOME}/.local/share/flutter-git-env"
readonly WRAPPER="${LIB_DIR}/wrapper.sh"
# Every SDK entry point that shells out to git to identify itself.
readonly TOOLS=(flutter dart)

log() { echo "$SCRIPT_NAME: $*"; }

fail() {
    echo "$SCRIPT_NAME: $*" >&2
    exit 1
}

write_wrapper() {
    mkdir -p "$LIB_DIR" "$BIN_DIR"
    cat > "$WRAPPER" <<'WRAPPER_EOF'
#!/bin/bash

# Strip the git-hook environment, then hand off to the real SDK binary.
# Installed by linux_configuration/fixes/fix_flutter_git_env.sh
# -- see that script for why this exists. Invoked through a symlink named
# after the tool it fronts (flutter, dart).

set -euo pipefail

tool="$(basename "$0")"
real="/usr/bin/${tool}"

[[ -x $real ]] || {
    echo "flutter-git-env: $real is missing or not executable" >&2
    exit 127
}

# Drop our own directory so a PATH lookup inside the real tool cannot find
# this wrapper again. The Flutter entry point does exactly such a lookup.
clean_path=""
IFS=':' read -r -a path_parts <<< "$PATH"
for part in "${path_parts[@]}"; do
    [[ $part == "$HOME/.local/bin" ]] && continue
    clean_path="${clean_path:+$clean_path:}$part"
done

# GIT_DIR is the one that actually bites; the rest are exported by git in the
# same breath and would mislead the SDK the same way.
exec env \
    -u GIT_DIR \
    -u GIT_WORK_TREE \
    -u GIT_INDEX_FILE \
    -u GIT_COMMON_DIR \
    -u GIT_OBJECT_DIRECTORY \
    -u GIT_ALTERNATE_OBJECT_DIRECTORIES \
    -u GIT_NAMESPACE \
    -u GIT_PREFIX \
    PATH="$clean_path" \
    "$real" "$@"
WRAPPER_EOF
    chmod +x "$WRAPPER"
}

link_tools() {
    local tool link
    for tool in "${TOOLS[@]}"; do
        link="${BIN_DIR}/${tool}"
        if [[ -e $link && ! -L $link ]]; then
            fail "$link exists and is not a symlink — refusing to overwrite it"
        fi
        ln -sfn "$WRAPPER" "$link"
        log "linked $link -> $WRAPPER"
    done
}

check_path() {
    case ":$PATH:" in
        *":$BIN_DIR:"*) ;;
        *) fail "$BIN_DIR is not on PATH — the wrapper would never be used" ;;
    esac
    local resolved
    for tool in "${TOOLS[@]}"; do
        resolved="$(command -v "$tool" || true)"
        [[ $resolved == "${BIN_DIR}/${tool}" ]] ||
            fail "$tool resolves to '$resolved', not the wrapper — check PATH order"
    done
}

# The real test: does the SDK still know what it is with GIT_DIR poisoned?
verify() {
    local probe_repo probe_version
    probe_repo="$(mktemp -d)"
    git -C "$probe_repo" init -q
    git -C "$probe_repo" -c user.email=x@y -c user.name=x commit -q --allow-empty -m probe

    probe_version="$(GIT_DIR="$probe_repo/.git" flutter --version 2>&1 | head -1 || true)"
    rm -rf "$probe_repo"

    if grep -q '0\.0\.0-unknown' <<< "$probe_version"; then
        fail "still broken: flutter reports an unknown SDK under GIT_DIR"
    fi
    if ! grep -q 'flutter/flutter' <<< "$probe_version"; then
        fail "still broken: flutter reports '$probe_version' under GIT_DIR"
    fi
    log "verified: $probe_version"
}

uninstall() {
    local tool link
    for tool in "${TOOLS[@]}"; do
        link="${BIN_DIR}/${tool}"
        if [[ -L $link && "$(readlink -f "$link")" == "$WRAPPER" ]]; then
            rm -f "$link"
            log "removed $link"
        fi
    done
    rm -rf "$LIB_DIR"
    log "uninstalled"
}

main() {
    case "${1:-}" in
        --uninstall)
            uninstall
            return
            ;;
        --check)
            [[ -x $WRAPPER ]] || fail "wrapper is not installed"
            check_path
            verify
            return
            ;;
        "") ;;
        *) fail "unknown option: $1 (expected --check or --uninstall)" ;;
    esac

    command -v flutter >/dev/null 2>&1 || fail "flutter is not on PATH"
    write_wrapper
    link_tools
    check_path
    verify
    log "done — flutter/dart now ignore an inherited GIT_DIR"
}

main "$@"
