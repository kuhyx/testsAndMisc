#!/bin/bash
# ============================================================================
# ci_mirror.sh — run the CI gates locally before a push can leave (monorepo).
#
# testsAndMisc variant of the repo-wide CI-mirror gate. Same idea as the
# single-package version: the installed pre-commit hook only checks staged
# files and the dev env already has every dependency, whereas CI runs
# `pre-commit run --all-files` and installs a fresh env from requirements.txt.
#
# Differences from the single-package version:
#   * requirements live at the repo root requirements.txt (what CI installs);
#   * tests run through meta/scripts/pytest_changed_packages.py rather than a
#     raw `pytest --cov=python_pkg` — this is the OOM-safe runner this machine
#     relies on (no xdist, bounded memory), chosen deliberately over the full
#     monorepo suite. It invokes pytest via sys.executable, so running it with
#     the clean venv's python routes coverage through the venv.
#
# Wired as the pre-push hook; a red result blocks the push before CI sees it.
# Escape hatch: `git push --no-verify`.
# ============================================================================

set -euo pipefail

REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-requirements.txt}"
readonly REQUIREMENTS_FILE

ROOT="$(git rev-parse --show-toplevel)"
readonly ROOT
cd "$ROOT"

readonly VENV_DIR="$ROOT/.ci-mirror-venv"
readonly HASH_FILE="$VENV_DIR/.requirements.sha256"
readonly REQ_PATH="$ROOT/$REQUIREMENTS_FILE"

log() { printf 'ci-mirror: %s\n' "$1" >&2; }

fail() {
    log "FAILED — $1"
    log "CI would be red. Fix the above, or 'git push --no-verify' to override."
    exit 1
}

require_file() {
    if [[ ! -f "$REQ_PATH" ]]; then
        fail "requirements file not found: $REQ_PATH"
    fi
}

# Rebuild the venv only when requirements.txt changed since the last build.
ensure_venv() {
    local current stored
    current="$(sha256sum "$REQ_PATH" | cut -d' ' -f1)"
    stored=""
    if [[ -f "$HASH_FILE" ]]; then
        stored="$(cat "$HASH_FILE")"
    fi

    if [[ -x "$VENV_DIR/bin/python" && "$current" == "$stored" ]]; then
        log "venv up to date (requirements.txt unchanged)"
        return
    fi

    log "requirements.txt changed — rebuilding clean venv (mirrors CI install)"
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip \
        || fail "pip self-upgrade in the clean venv"
    "$VENV_DIR/bin/python" -m pip install --quiet -r "$REQ_PATH" \
        || fail "pip install -r $REQUIREMENTS_FILE (a dep may be undeclared)"
    printf '%s' "$current" > "$HASH_FILE"
    log "clean venv ready"
}

run_precommit_all_files() {
    # Skip pytest-coverage here: it is a pre-commit-stage hook that would run
    # in the system env (not our clean venv) and duplicate run_pytest below.
    log "pre-commit run --all-files (mirrors the pre-commit workflow)"
    SKIP=pytest-coverage pre-commit run --all-files || fail "pre-commit --all-files"
}

run_pytest_clean_venv() {
    log "changed-packages pytest in the clean venv (OOM-safe runner)"
    "$VENV_DIR/bin/python" meta/scripts/pytest_changed_packages.py \
        || fail "pytest_changed_packages (clean requirements.txt venv)"
}

main() {
    require_file
    ensure_venv
    run_precommit_all_files
    run_pytest_clean_venv
    log "all CI gates passed locally — safe to push"
}

main "$@"
