#!/usr/bin/env bash

# ============================================================================
# install_hooks.sh — make this clone's git hooks active and its toolchain complete.
#
# Run once per machine / per fresh clone:
#   ./meta/scripts/install_hooks.sh
#
# This is the bootstrap that the hooks themselves cannot perform: if
# core.hooksPath is unset and .git/hooks is empty, git runs nothing at all, so
# no hook is around to repair the wiring. Everything after that first run is
# self-healing — each hook re-asserts core.hooksPath and verifies the toolchain.
#
# Note: `pre-commit install` is deliberately NOT used. It writes into
# .git/hooks/, which git ignores entirely while core.hooksPath is set, and
# newer pre-commit refuses outright. The hooks in linux_configuration/.githooks/
# invoke `pre-commit run` directly instead, and being tracked they cannot go
# missing on a clone.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME

usage() {
	echo "Usage: $SCRIPT_NAME [--check]"
	echo "Options:"
	echo "  --check   Verify wiring and toolchain, change nothing, exit 1 if incomplete"
	echo "  -h,--help Show this help"
	exit 0
}

CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
	case $1 in
	--check)
		CHECK_ONLY=true
		shift
		;;
	-h | --help)
		usage
		;;
	*)
		echo "Unknown option: $1" >&2
		exit 1
		;;
	esac
done

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

# shellcheck source=linux_configuration/.githooks/lib/common.sh
source "${repo_root}/linux_configuration/.githooks/lib/common.sh"

# Every hook that must exist and be executable for the gate to be complete.
readonly MANAGED_HOOKS=(pre-commit pre-push)

# Report on wiring/toolchain without changing anything; non-zero when incomplete.
run_check() {
	local failures=0 current hook path

	current="$(git config --get core.hooksPath || true)"
	if [[ $current == "$HOOKS_PATH_REL" ]]; then
		echo "✓ core.hooksPath = ${HOOKS_PATH_REL}"
	else
		echo "✗ core.hooksPath is '${current:-<unset>}', expected '${HOOKS_PATH_REL}'" >&2
		failures=$((failures + 1))
	fi

	for hook in "${MANAGED_HOOKS[@]}"; do
		path="${HOOKS_PATH_REL}/${hook}"
		if [[ -x $path ]]; then
			echo "✓ ${hook} hook present and executable"
		else
			echo "✗ ${hook} hook missing or not executable: ${path}" >&2
			failures=$((failures + 1))
		fi
	done

	local entry cmd
	for entry in "${REQUIRED_TOOLS[@]}"; do
		cmd="${entry%%:*}"
		if command -v "$cmd" >/dev/null 2>&1; then
			echo "✓ ${cmd}"
		else
			echo "✗ ${cmd} not installed" >&2
			failures=$((failures + 1))
		fi
	done

	if ((failures > 0)); then
		echo "" >&2
		echo "${failures} problem(s). Run ./meta/scripts/install_hooks.sh to fix." >&2
		return 1
	fi

	echo ""
	echo "Hooks are wired and the toolchain is complete."
}

# Point git at the tracked hooks directory and make the hooks runnable.
install_wiring() {
	local hook path

	ensure_hooks_path
	echo "✓ core.hooksPath = ${HOOKS_PATH_REL}"

	for hook in "${MANAGED_HOOKS[@]}"; do
		path="${HOOKS_PATH_REL}/${hook}"
		if [[ ! -f $path ]]; then
			hook_abort "Aborted: ${path} is missing from the working tree. The hooks are tracked in git — restore them with 'git checkout -- ${path}'."
		fi
		chmod +x "$path"
		echo "✓ ${hook} hook executable"
	done
}

main() {
	if [[ $CHECK_ONLY == true ]]; then
		run_check
		return
	fi

	echo "Wiring git hooks..."
	install_wiring

	echo ""
	echo "Verifying toolchain..."
	verify_toolchain
	echo "✓ all ${#REQUIRED_TOOLS[@]} required tools present"

	echo ""
	echo "Pre-building pre-commit hook environments..."
	pre-commit install-hooks

	echo ""
	echo "Done. Commits run the pre-commit stage; pushes run prettier, ci-mirror,"
	echo "and pytest-coverage. Verify any time with:"
	echo "  ./meta/scripts/install_hooks.sh --check"
}

main "$@"
