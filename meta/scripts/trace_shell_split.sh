#!/usr/bin/env bash

# ============================================================================
# Capture an execution trace of a shell script with every mutating command
# stubbed, so a split can be verified by RUNNING it rather than by sourcing it.
#
# Why this exists: verify_shell_split.sh sources the libs and never calls them,
# which proves `source` lines resolve and nothing more. The analyze_repo.sh
# split passed that, plus bash -n, shellcheck and a function-set diff, and
# still shipped a script that aborted after language detection -- a `set -e`
# function-tail return and a self-referencing nameref, neither reachable
# without execution. See docs/shell-split-verification.md.
#
# The trace is the artifact: run this at the pre-split commit and again after
# the split, then diff. An identical trace means the same commands ran in the
# same order with the same arguments.
#
# Mutating binaries are shadowed by stubs earlier on PATH, so the live system
# is never touched. That is what makes this safe for the enforcement and
# installer scripts Decision 6 forbids executing for real.
#
# Scripts whose job is PLACING FILES need --prefix: shell redirections cannot
# be stubbed via PATH, so without it the choice is an empty trace or a rewritten
# live system. See lib/trace_prefix.sh for the two layers that solves.
#
# Usage:
#   trace_shell_split.sh <script> [-- <script args>]
#   trace_shell_split.sh <script> --out <file> [-- <script args>]
#   trace_shell_split.sh <script> --stub git,curl,makepkg --out <file>
#   trace_shell_split.sh <script> --prefix <dir> [--bind-abs /etc/modprobe.d]
# ============================================================================

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME

# readlink -f, not dirname alone: this repo's root-level entry points are
# symlinks into meta/, and an unresolved SCRIPT_DIR turns a source line into an
# instant exit under set -e. See docs/shell-split-verification.md.
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
readonly SCRIPT_DIR
# shellcheck source=lib/trace_prefix.sh
source "$SCRIPT_DIR/lib/trace_prefix.sh"
# shellcheck source=lib/trace_stubs.sh
source "$SCRIPT_DIR/lib/trace_stubs.sh"

TARGET=""
OUT=""
TEMP_DIR=""
PREFIX=""
declare -a SCRIPT_ARGS=()
declare -a EXTRA_STUBS=()
declare -a BIND_ABS=()

cleanup() {
	if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
		rm -rf "$TEMP_DIR"
	fi
}

trap cleanup EXIT

usage() {
	echo "Usage: $SCRIPT_NAME <script> [--out <file>] [--stub a,b] [-- <script args>]"
	echo "  <script>      script to trace (not modified)"
	echo "  --out <file>  write the trace here (default: stdout)"
	echo "  --stub a,b    also shadow these binaries (e.g. git,curl,makepkg)"
	echo "  --prefix <d>  redirect HOME/XDG writes into <d> and list them"
	echo "  --bind-abs <p>  bind absolute path <p> into the prefix (repeatable)"
	echo "  --            everything after this is passed to the script"
	exit 0
}

validate_requirements() {
	if [[ -z "$TARGET" ]]; then
		echo "Error: no script given" >&2
		exit 1
	fi
	if [[ ! -f "$TARGET" ]]; then
		echo "Error: no such script: $TARGET" >&2
		exit 1
	fi
	# Refuse rather than quietly writing to the real path: a script with
	# hardcoded absolute destinations and no --bind-abs would either mutate the
	# live system or take a different branch on EPERM, and both look like a
	# clean trace.
	if [[ -n "$PREFIX" && ${#BIND_ABS[@]} -eq 0 ]]; then
		local -a found=()
		mapfile -t found < <(trace_prefix_scan_absolute "$TARGET")
		if [[ ${#found[@]} -gt 0 ]]; then
			echo "Error: $TARGET writes to absolute paths; pass --bind-abs for each:" >&2
			printf '  --bind-abs %s\n' "${found[@]}" >&2
			exit 1
		fi
	fi
}

main() {
	validate_requirements

	TEMP_DIR="$(mktemp -d)"
	if [[ ! -d "$TEMP_DIR" ]]; then
		echo "Error: failed to create temporary directory" >&2
		exit 1
	fi

	local bin_dir="$TEMP_DIR/bin"
	local trace="$TEMP_DIR/trace.txt"
	: >"$trace"
	write_stubs "$bin_dir" ${EXTRA_STUBS[@]+"${EXTRA_STUBS[@]}"}

	# xtrace to a dedicated fd so the script's own stdout stays separate.
	local xtrace="$TEMP_DIR/xtrace.txt"

	# Under --prefix the run happens inside bwrap when absolute destinations
	# were bound; otherwise it is a plain subshell with a redirected HOME.
	local -a runner=()
	if [[ -n "$PREFIX" && ${#BIND_ABS[@]} -gt 0 ]]; then
		mapfile -t runner < <(trace_prefix_bwrap_argv "$PREFIX" "${BIND_ABS[@]}" --)
	fi

	set +e
	(
		export TRACE_FILE="$trace"
		export PATH="$bin_dir:$PATH"
		if [[ -n "$PREFIX" ]]; then
			local assignment
			while IFS= read -r assignment; do
				export "${assignment?}"
			done < <(trace_prefix_env "$PREFIX")
		fi
		exec 9>"$xtrace"
		export BASH_XTRACEFD=9
		set -x
		"${runner[@]+"${runner[@]}"}" bash "$TARGET" "${SCRIPT_ARGS[@]+"${SCRIPT_ARGS[@]}"}"
	) >"$TEMP_DIR/stdout.txt" 2>"$TEMP_DIR/stderr.txt"
	local status=$?
	set -e

	{
		echo "=== exit status: $status"
		echo "=== mutating calls (stubbed)"
		cat "$trace"
		# Emitted only under --prefix, so traces taken without the flag stay
		# byte-identical to the ones already captured.
		if [[ -n "$PREFIX" ]]; then
			echo "=== files written (prefix)"
			trace_prefix_manifest "$PREFIX"
		fi
		echo "=== stdout"
		sed "s#${PREFIX:-__no_prefix__}#@PREFIX@#g" "$TEMP_DIR/stdout.txt"
		echo "=== stderr"
		sed "s#${PREFIX:-__no_prefix__}#@PREFIX@#g" "$TEMP_DIR/stderr.txt"
	} >"${OUT:-/dev/stdout}"
}

while [[ $# -gt 0 ]]; do
	case $1 in
	--out)
		OUT="$2"
		shift 2
		;;
	--stub)
		# Comma-separated extra binaries to shadow for this run only.
		IFS=',' read -r -a EXTRA_STUBS <<<"$2"
		shift 2
		;;
	--prefix)
		PREFIX="$2"
		shift 2
		;;
	--bind-abs)
		BIND_ABS+=("$2")
		shift 2
		;;
	-h | --help)
		usage
		;;
	--)
		shift
		SCRIPT_ARGS=("$@")
		break
		;;
	*)
		if [[ -z "$TARGET" ]]; then
			TARGET="$1"
			shift
		else
			echo "Unknown option: $1" >&2
			exit 1
		fi
		;;
	esac
done

main "$@"
