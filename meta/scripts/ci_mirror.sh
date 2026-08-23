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
#
# SCOPE (2026-08-23): this gate used to run `--all-files` plus every shell
# suite on every push, costing ~130s. It now checks the PUSH RANGE:
#   * pre-commit runs over the pushed files, not the whole tree. Repo-wide
#     hooks are `always_run`/`--all` in the config and still sweep everything.
#   * only the lib/tests suites whose tree the push touched are run.
#   * pytest runs only when the push touches Python -- but then runs the WHOLE
#     suite, because the coverage bar is whole-repo.
#   * a tree hash identical to the last green run short-circuits the lot.
# Any change to the gate's own machinery or to .pre-commit-config.yaml forces
# a full sweep, so a new rule cannot land while only checking its own diff.
# ============================================================================

set -euo pipefail

REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-requirements.txt}"
readonly REQUIREMENTS_FILE

ROOT="$(git rev-parse --show-toplevel)"
readonly ROOT
cd "$ROOT"

# shellcheck source=meta/scripts/ci_mirror_range.sh
source "$ROOT/meta/scripts/ci_mirror_range.sh"
# shellcheck source=meta/scripts/ci_mirror_shell.sh
source "$ROOT/meta/scripts/ci_mirror_shell.sh"

# Records the tree hash of the last fully-green run; see tree_cache_*.
readonly GREEN_CACHE="$ROOT/.ci-mirror-venv/.last-green-tree"

LOGDIR=""

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
	if [[ -n "$LOGDIR" && -d "$LOGDIR" ]]; then
		rm -rf "$LOGDIR"
	fi
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

	local paths
	paths="$(changed_paths)"

	local scope_args=(--all-files)
	if ! needs_full_sweep "$paths"; then
		scope_args=(--from-ref "$PRE_COMMIT_FROM_REF" --to-ref "$PRE_COMMIT_TO_REF")
		log "scoped to the push range ($(grep -c . <<<"$paths") file(s) changed)"
	else
		log "full sweep (no push range, or the gate's own config changed)"
	fi

	# The three stages are independent, so they run concurrently and the gate
	# costs the slowest rather than the sum. Output goes to per-stage files and
	# is replayed on failure: interleaved live output from three stages is
	# unreadable, and the diagnosis is what makes a red gate actionable.
	local logdir
	logdir="$(mktemp -d -t ci-mirror-logs-XXXXXX)"
	LOGDIR="$logdir"

	# Skip pytest-coverage here: it is a pre-commit-stage hook that would run
	# in the system env (not our clean venv) and duplicate the pytest run below.
	log "pre-commit (mirrors the pre-commit workflow)"
	(cd "$CHECKOUT" && SKIP=pytest-coverage pre-commit run "${scope_args[@]}") \
		>"$logdir/precommit.log" 2>&1 &
	local pc_pid=$!

	run_python_gate "$paths" >"$logdir/pytest.log" 2>&1 &
	local py_pid=$!

	# The shell gate is NOT backgrounded alongside the others when it contains a
	# jailed suite: two coverage jails, or a jail racing a busy CPU, produce
	# false failures (measured repeatedly). It runs after the parallel pair.
	local pc_rc=0 py_rc=0
	wait "$pc_pid" || pc_rc=$?
	wait "$py_pid" || py_rc=$?

	if ((pc_rc != 0)); then
		cat "$logdir/precommit.log" >&2
		fail "pre-commit (scoped run)"
	fi
	if ((py_rc != 0)); then
		cat "$logdir/pytest.log" >&2
		fail "pytest_changed_packages (clean requirements.txt venv)"
	fi

	run_shell_test_gate "$paths"
}

# Run the whole python suite, but only when the push touches Python.
#
# NOTE: pytest_changed_packages.py returns 0 immediately when given no
# arguments (it is normally a pre-commit hook fed staged paths). Invoking it
# bare -- as this gate did until 2026-08-23 -- therefore ran ZERO tests and
# reported success on every push. The changed paths are passed explicitly so
# the stage actually executes.
run_python_gate() {
	local paths="$1"
	if ! touches_python "$paths" && ! needs_full_sweep "$paths"; then
		log "no Python in the push range — skipping pytest"
		return 0
	fi
	log "whole python_pkg suite in the clean venv (OOM-safe runner)"
	local args=()
	while IFS= read -r f; do
		[[ -n "$f" ]] && args+=("$f")
	done <<<"$paths"
	# A full sweep has no range; hand it a sentinel so the runner does not
	# short-circuit on empty argv.
	((${#args[@]} == 0)) && args=(--all)
	(cd "$CHECKOUT" && "$VENV_DIR/bin/python" meta/scripts/pytest_changed_packages.py "${args[@]}")
}

# Short-circuit a re-push of a tree that already passed.
#
# Keyed on the whole-repo tree hash of HEAD, so it self-invalidates when
# anything in the tree changes -- including the gate's own scripts. A rebase
# that lands the identical tree, or a retried push after a network failure,
# then costs nothing. The record lives inside .ci-mirror-venv/ (already
# gitignored) so it never shows up in `git status` or a jail fingerprint.
tree_is_known_green() {
	local head_tree stored
	head_tree="$(git -C "$ROOT" rev-parse 'HEAD^{tree}')"
	[[ -f "$GREEN_CACHE" ]] || return 1
	stored="$(cat "$GREEN_CACHE")"
	[[ "$head_tree" == "$stored" ]]
}

record_tree_green() {
	git -C "$ROOT" rev-parse 'HEAD^{tree}' >"$GREEN_CACHE" 2>/dev/null || true
}

main() {
	require_file
	if tree_is_known_green; then
		log "this exact tree already passed the full gate — nothing to redo"
		exit 0
	fi
	ensure_venv
	run_gates_in_clean_worktree
	record_tree_green
	log "all CI gates passed locally — safe to push"
}

main "$@"
