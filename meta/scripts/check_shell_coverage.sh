#!/usr/bin/env bash

# ============================================================================
# Ratchet: every shell library must live beside a test suite that runs it.
#
# This is a PRESENCE gate, not a percentage gate. Phase 1 measured why: the
# decision logic in these libs reaches ~90% under test, while the effecting
# code reaches 0% because it sudo-writes, pkills, or installs packages. A
# numeric bar would therefore be unreachable without either shimming every
# external for every installer or adding the suppressions this repo forbids.
# What is enforceable — and what actually catches regressions — is that a lib
# directory has a run_all.sh which sources and exercises it.
#
# Scope is libraries under a lib/ directory. Entry scripts are orchestration
# whose bodies are the untestable part, so capping them would buy nothing.
#
# The ratchet: files listed in the allowlist predate the gate and are exempt.
# A file that is NEW or MODIFIED must be covered, and a covered file can never
# go back on the allowlist. The list only ever shrinks.
#
#   check_shell_coverage.sh <file>...   # gate the named files (hook mode)
#   check_shell_coverage.sh --all       # report every uncovered lib
#   check_shell_coverage.sh --seed      # rewrite the allowlist from HEAD
#
# Exits 0 when every checked file is covered or exempt, 1 otherwise.
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
REPO_ROOT="$(git rev-parse --show-toplevel)"
readonly REPO_ROOT
readonly ALLOWLIST="$REPO_ROOT/meta/shell-coverage-allowlist.txt"

usage() {
	echo "Usage: $SCRIPT_NAME [--all | --seed | <file>...]"
	echo "Options:"
	echo "  --all         Report every uncovered shell library"
	echo "  --seed        Rewrite the allowlist from the current tree"
	echo "  -h, --help    Show this help"
	echo
	echo "A shell library is covered when its lib/ directory has a"
	echo "tests/run_all.sh suite. Listed files are exempt until modified."
	exit 0
}

# True for a shell library: a .sh under a lib/ dir, excluding the tests
# themselves and vendored trees. Payloads are data emitted onto other
# machines, not logic this repo's suites can source.
#
# Both nestings of "library" and "tests" are test code and are out of scope:
# lib/tests/ (a suite beside its libs) and tests/lib/ (helpers beside their
# tests). Missing the second made the gate demand tests/lib/tests/run_all.sh,
# which is incoherent — and it would have fired precisely while editing test
# helpers to add the suites this ratchet asks for.
is_shell_lib() {
	local path="$1"
	[[ "$path" == *.sh ]] || return 1
	[[ "$path" == */lib/* ]] || return 1
	[[ "$path" == */lib/tests/* ]] && return 1
	[[ "$path" == */tests/lib/* ]] && return 1
	[[ "$path" == */lib/payloads/* ]] && return 1
	[[ "$path" == third_party/* ]] && return 1
	return 0
}

# A lib is covered when a run_all.sh sits in its directory's tests/ subdir.
is_covered() {
	local path="$1"
	[[ -f "$(dirname "$path")/tests/run_all.sh" ]]
}

collect_libs() {
	git -C "$REPO_ROOT" ls-files '*.sh'
}

# Every in-scope lib that has no suite beside it.
report_uncovered() {
	local path
	for path in "$@"; do
		is_shell_lib "$path" || continue
		[[ -f "$REPO_ROOT/$path" ]] || continue
		is_covered "$REPO_ROOT/$path" || printf '%s\n' "$path"
	done
}

seed_allowlist() {
	local -a libs=()
	mapfile -t libs < <(collect_libs)

	# Shrink-only, enforced rather than merely documented: a reseed may drop
	# entries that gained a suite, never add one. Without this, running --seed
	# after writing an untested library would silently exempt it and quietly
	# widen the hole the gate exists to close.
	if [[ -f "$ALLOWLIST" ]]; then
		local -a added=()
		mapfile -t added < <(comm -13 \
			<(exempt_paths | sort) \
			<(report_uncovered "${libs[@]}" | sort))

		if ((${#added[@]} > 0)); then
			echo "$SCRIPT_NAME: refusing to seed — that would ADD ${#added[@]} entr(ies):" >&2
			local entry
			for entry in "${added[@]}"; do
				printf '  %s\n' "$entry" >&2
			done
			echo >&2
			echo "  The allowlist only ever shrinks. Give these libraries a" >&2
			echo "  tests/run_all.sh instead of exempting them." >&2
			return 1
		fi
	fi

	{
		echo "# Shell libraries that predate the coverage ratchet."
		echo "#"
		echo "# Each line is a file exempt from check_shell_coverage.sh until it is"
		echo "# next modified. Modifying an exempt file requires giving its lib/"
		echo "# directory a tests/run_all.sh suite and deleting the line."
		echo "#"
		echo "# This list only ever shrinks. Never add a path to it by hand -- a new"
		echo "# library must ship with its tests."
		echo "#"
		echo "# Regenerate (only ever to REMOVE now-covered entries):"
		echo "#   bash meta/scripts/check_shell_coverage.sh --seed"
		report_uncovered "${libs[@]}" | sort
	} >"$ALLOWLIST"

	local count
	count="$(grep -cv '^#' "$ALLOWLIST" || true)"
	echo "$SCRIPT_NAME: seeded allowlist with $count uncovered librar(ies)"
}

# The allowlist minus its comment lines.
exempt_paths() {
	[[ -f "$ALLOWLIST" ]] || return 0
	grep -v '^#' "$ALLOWLIST" | grep -v '^[[:space:]]*$' || true
}

is_exempt() {
	local path="$1" entry
	while IFS= read -r entry; do
		[[ "$entry" == "$path" ]] && return 0
	done < <(exempt_paths)
	return 1
}

# Gate the named files: uncovered AND not exempt is a failure.
check_files() {
	local -a offenders=()
	local path

	while IFS= read -r path; do
		[[ -n "$path" ]] || continue
		is_exempt "$path" || offenders+=("$path")
	done < <(report_uncovered "$@")

	if ((${#offenders[@]} == 0)); then
		echo "$SCRIPT_NAME: every checked shell library has a test suite"
		return 0
	fi

	echo "$SCRIPT_NAME: ${#offenders[@]} shell librar(ies) without a test suite:" >&2
	for path in "${offenders[@]}"; do
		printf '  %s\n' "$path" >&2
		printf '    needs: %s/tests/run_all.sh\n' "$(dirname "$path")" >&2
	done
	echo >&2
	echo "  A new or modified shell library must ship with a suite that" >&2
	echo "  sources it. Extend the nearest existing tests/ directory rather" >&2
	echo "  than cloning a harness -- jscpd fails above 2% duplication." >&2
	return 1
}

report_all() {
	local -a libs=()
	mapfile -t libs < <(collect_libs)

	local uncovered exempt_count total
	uncovered="$(report_uncovered "${libs[@]}")"
	exempt_count="$(exempt_paths | wc -l)"
	total="$(printf '%s\n' "$uncovered" | grep -c . || true)"

	echo "$SCRIPT_NAME: $total uncovered shell librar(ies), $exempt_count exempt"

	local path
	while IFS= read -r path; do
		[[ -n "$path" ]] || continue
		if is_exempt "$path"; then
			printf '  exempt  %s\n' "$path"
		else
			printf '  BLOCK   %s\n' "$path"
		fi
	done <<<"$uncovered"
}

main() {
	if [[ $# -eq 0 ]]; then
		echo "Error: pass --all, --seed, or one or more file paths" >&2
		exit 1
	fi

	case "$1" in
	--seed)
		seed_allowlist
		;;
	--all)
		report_all
		;;
	*)
		check_files "$@"
		;;
	esac
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	-h | --help)
		usage
		;;
	*)
		break
		;;
	esac
done

main "$@"
