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

	run_shell_test_gate
}

# Mirror the shell-tests workflow's side-effect-free half.
#
# Without this, ci-mirror covered the pre-commit and python-tests workflows but
# not Shell tests, so a shell change could pass every local gate and still go
# red on push — which is exactly what happened repeatedly during the
# 250-line-cap campaign: three separate test files asserted on code that a
# split had moved, and each was only caught after the push.
#
# The Arch-container half of that workflow is deliberately NOT mirrored: it
# needs an Arch userland running as root to touch /etc, which is what the
# disposable container provides and a developer machine must not.
# A suite that writes to real system paths declares it with a `jail_args` file
# beside its run_all.sh, holding the --bind/--seed-* flags it needs. Such a
# suite REFUSES to run bare -- that guard is what stops a test run from
# rewriting the developer's own /etc -- so invoking it directly fails the gate.
#
# Fails closed: a marker present but empty is a mistake, not a licence to skip.
run_jailed_suite() {
	local runner="$1"
	local args_file="$CHECKOUT/${runner%/run_all.sh}/jail_args"

	local jail_args=()
	while IFS= read -r arg; do
		jail_args+=("$arg")
	done < <(grep -v '^#\|^$' "$args_file" || true)

	if [[ ${#jail_args[@]} -eq 0 ]]; then
		fail "jail_args is present but empty: $args_file"
	fi

	(cd "$CHECKOUT" && bash meta/scripts/shell_coverage_jail.sh \
		--subject "$runner" "${jail_args[@]}" -- "" >/dev/null) ||
		fail "jailed lib/tests suite failed: $runner"
}

run_shell_test_gate() {
	log "lib/tests suites (mirrors the shell-tests workflow)"
	local runners=()
	while IFS= read -r runner; do
		runners+=("$runner")
	done < <(cd "$CHECKOUT" && find . -path ./node_modules -prune -o \
		-path '*/lib/tests/run_all.sh' -print | sort)

	if [[ ${#runners[@]} -eq 0 ]]; then
		fail "no lib/tests/run_all.sh found — the discovery glob is wrong"
	fi

	local runner
	for runner in "${runners[@]}"; do
		if [[ -f "$CHECKOUT/${runner%/run_all.sh}/jail_args" ]]; then
			run_jailed_suite "$runner"
		else
			(cd "$CHECKOUT" && "$runner" >/dev/null) ||
				fail "lib/tests suite failed: $runner"
		fi
	done

	log "side-effect-free shell tests (mirrors the shell-tests workflow)"
	# Parsed OUT of the workflow rather than duplicated here. A hardcoded copy
	# drifts the moment someone adds a test to the workflow, and a mirror that
	# silently checks less than CI is worse than no mirror: it reports safe.
	# The awk range is the shell-tests job's `tests=( ... )` array, taking the
	# first one only — the second belongs to the Arch container job, which is
	# deliberately not mirrored.
	local shell_tests=()
	while IFS= read -r shell_test; do
		shell_tests+=("$shell_test")
	done < <(awk '/^ *tests=\(/{n++} n==1 && /^ *test_.*\.sh *$/{gsub(/ /,"");print} n==1 && /^ *\)/{exit}' \
		"$CHECKOUT/.github/workflows/shell-tests.yml")

	if [[ ${#shell_tests[@]} -eq 0 ]]; then
		fail "could not parse the test list out of shell-tests.yml"
	fi

	local shell_test
	for shell_test in "${shell_tests[@]}"; do
		(cd "$CHECKOUT" && bash "linux_configuration/tests/$shell_test" >/dev/null 2>&1) ||
			fail "shell test failed: $shell_test"
	done
}

main() {
	require_file
	ensure_venv
	run_gates_in_clean_worktree
	log "all CI gates passed locally — safe to push"
}

main "$@"
