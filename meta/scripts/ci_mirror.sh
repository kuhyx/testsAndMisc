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
	"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip ||
		fail "pip self-upgrade in the clean venv"
	"$VENV_DIR/bin/python" -m pip install --quiet -r "$REQ_PATH" ||
		fail "pip install -r $REQUIREMENTS_FILE (a dep may be undeclared)"
	printf '%s' "$current" >"$HASH_FILE"
	log "clean venv ready"
}

# Disposable clean checkout of HEAD; see run_gates_in_clean_worktree.
CHECKOUT=""

cleanup_checkout() {
	if [[ -n "$CHECKOUT" && -d "$CHECKOUT" ]]; then
		git -C "$ROOT" worktree remove --force "$CHECKOUT" >/dev/null 2>&1 || true
		rm -rf "$CHECKOUT"
		git -C "$ROOT" worktree prune >/dev/null 2>&1 || true
	fi
}

trap cleanup_checkout EXIT

# Run the gates against a throwaway worktree at HEAD rather than the live tree.
#
# `pre-commit run --all-files` stashes unstaged changes, runs the hooks, then
# restores. In a shared checkout that is actively hostile: when another agent
# (or the user) has uncommitted work that collides with a hook's auto-fix, the
# restore conflicts, pre-commit rolls the fixes back, and the push fails with a
# diagnostic that points at the innocent hook rather than at the collision.
# Worse, the stash window puts someone else's uncommitted work at risk, which
# is exactly what memories/git-rules.md forbids.
#
# A clean worktree removes the stash entirely and is a truer mirror of CI,
# which always builds from a pristine checkout and never sees a dirty file.
run_gates_in_clean_worktree() {
	CHECKOUT="$(mktemp -d -t ci-mirror-XXXXXX)"
	rm -rf "$CHECKOUT"
	log "checking out HEAD into a clean worktree (no stash of your tree)"
	git -C "$ROOT" worktree add --detach --quiet "$CHECKOUT" HEAD ||
		fail "could not create the clean worktree"

	# Skip pytest-coverage here: it is a pre-commit-stage hook that would run
	# in the system env (not our clean venv) and duplicate the pytest run below.
	log "pre-commit run --all-files (mirrors the pre-commit workflow)"
	(cd "$CHECKOUT" && SKIP=pytest-coverage pre-commit run --all-files) ||
		fail "pre-commit --all-files"

	log "changed-packages pytest in the clean venv (OOM-safe runner)"
	(cd "$CHECKOUT" && "$VENV_DIR/bin/python" meta/scripts/pytest_changed_packages.py) ||
		fail "pytest_changed_packages (clean requirements.txt venv)"
}

main() {
	require_file
	ensure_venv
	run_gates_in_clean_worktree
	log "all CI gates passed locally — safe to push"
}

main "$@"
