#!/usr/bin/env bash

# ============================================================================
# Measure a shell script's line coverage while it runs FOR REAL, inside a
# throwaway user+mount namespace.
#
#   shell_coverage_jail.sh --subject <file> [options] -- <case> [<case>...]
#
# Why a namespace and not just PATH shims: PATH shims cannot intercept a bare
# `cat >/etc/foo` (there is no binary to shadow), and they cannot make the
# root half of `if [[ $EUID -ne 0 ]]` execute. Measured on
# setup_night_lockdown.sh: PATH shims alone plateau at 81.58%; adding
# --map-root-user reaches 86.84%; bind-mounting every write target reaches
# 100.00% (38/38) with NO source changes and NO suppressions.
#
# Three facts that cost real time to find, all load-bearing:
#
#   1. --map-root-user ALONE does not grant writes to real-root-owned files.
#      CAP_DAC_OVERRIDE inside a userns only covers files whose owner uid is
#      mapped in, so /etc/... stays unwritable until it is bind-mounted.
#   2. The jail needs its own passwd/group/nsswitch. Inside the userns the
#      invoking user does not resolve, so `id -u "$USER"` fails and aborts the
#      subject under `set -e` long before the interesting code.
#   3. Mount only what the subject WRITES; preserve what it READS. A blanket
#      jail that masked /usr/local/bin cut pacman_wrapper.sh from 75.00% to
#      28.95%: the wrapper sources its siblings from there and took its
#      "libraries missing" escape hatch. Over-mounting looks like dead code.
#
# Entry scripts must be executed in place: they resolve libs via BASH_SOURCE
# and common.sh via `readlink -f "$0"`, so staging a copy breaks them.
# ============================================================================

set -euo pipefail

readonly SCRIPT_NAME="${0##*/}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly REPO_ROOT

SUBJECT=""
MEASURE=""
SEED_DIRS=()
SEED_FILES=()
MIN_PERCENT=100
# Per-case wall-clock ceiling. A hung case cannot be distinguished from a slow
# one without a bound, and an unbounded run blocks a hook indefinitely.
CASE_TIMEOUT="120s"
# Off by default: when MEASURING, a case that exits non-zero is normal and
# wanted -- the usage example's `bogus` case exists precisely to cover an
# error path. Only a GATE, whose subject is a test suite, wants that status
# to fail the run. See --fail-on-case-error.
FAIL_ON_CASE_ERROR=0
BIND_PATHS=()
EXTRA_SHIMS=()
CASES=()

usage() {
	cat <<USAGE
Usage: $SCRIPT_NAME --subject <file> [options] -- <case> [<case>...]

  --subject <file>   the script to RUN (required)
  --measure <name>   basename of the file to measure coverage OF; defaults to
                     the subject. Differs when the subject is a test suite
                     and the file of interest is the lib that suite drives.
  --bind <path>      bind-mount <path> to an empty jail dir; repeatable.
                     Use for every path the subject WRITES. Do NOT bind a
                     path the subject READS from -- that masks its inputs.
  --shim <name>      additionally stub <name> on PATH; repeatable
  --seed-dir <path>  create <path> inside the jail; repeatable. Needed when a
                     subject targets a platform this host is not -- a Debian
                     script writing /etc/php/8.2/apache2/ finds nothing to
                     mirror on an Arch box.
  --seed-file <path> create an empty file at <path> inside the jail
  --timeout <dur>    per-case wall-clock ceiling (default 120s)
  --min <percent>    fail below this (default 100)
  --fail-on-case-error
                     exit non-zero if any case exits non-zero. For GATE use,
                     where the subject is a test suite and a failing
                     assertion must fail the run. Off by default: when
                     measuring, an error-path case exiting non-zero is the
                     point of running it.
  -- <case>...       one invocation each; "" means "no arguments"

Example:
  $SCRIPT_NAME --subject setup_night_lockdown.sh \\
      --bind /etc --bind /usr/local/bin --bind /var/lib \\
      -- help status bogus setup unlock
USAGE
	exit 0
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--subject)
		SUBJECT="$2"
		shift 2
		;;
	--measure)
		MEASURE="$2"
		shift 2
		;;
	--bind)
		BIND_PATHS+=("$2")
		shift 2
		;;
	--shim)
		EXTRA_SHIMS+=("$2")
		shift 2
		;;
	--seed-dir)
		SEED_DIRS+=("$2")
		shift 2
		;;
	--seed-file)
		SEED_FILES+=("$2")
		shift 2
		;;
	--timeout)
		CASE_TIMEOUT="$2"
		shift 2
		;;
	--min)
		MIN_PERCENT="$2"
		shift 2
		;;
	--fail-on-case-error)
		FAIL_ON_CASE_ERROR=1
		shift
		;;
	-h | --help) usage ;;
	--)
		shift
		CASES=("$@")
		break
		;;
	*)
		echo "Unknown option: $1" >&2
		exit 1
		;;
	esac
done

validate_requirements() {
	if [[ -z $SUBJECT ]]; then
		echo "Error: --subject is required" >&2
		exit 1
	fi
	if [[ ! -f $SUBJECT ]]; then
		echo "Error: no such subject: $SUBJECT" >&2
		exit 1
	fi
	if [[ ${#CASES[@]} -eq 0 ]]; then
		echo "Error: at least one case is required after --" >&2
		exit 1
	fi
	local tool
	for tool in kcov unshare python3; do
		if ! command -v "$tool" >/dev/null 2>&1; then
			echo "Error: $tool is not installed" >&2
			exit 1
		fi
	done
}

JAIL=""
cleanup() {
	if [[ -n $JAIL && -d $JAIL ]]; then
		rm -rf "$JAIL"
	fi
}
trap cleanup EXIT

# Jail construction, including the shim list, lives in
# lib/shell_coverage_jail_setup.sh (250-line cap).
# shellcheck source=./lib/shell_coverage_jail_setup.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib/shell_coverage_jail_setup.sh"

# The in-namespace case runner, likewise split for the 250-line cap.
# shellcheck source=./lib/shell_coverage_case_runner.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib/shell_coverage_case_runner.sh"

main() {
	validate_requirements
	build_jail
	write_cases
	build_mount_script

	local subject_abs subject_dir subject_base measure_base
	subject_abs="$(readlink -f "$SUBJECT")"
	subject_dir="$(dirname "$subject_abs")"
	subject_base="$(basename "$subject_abs")"
	measure_base="${MEASURE:-$subject_base}"

	# A pre-run fingerprint of the working tree. Fact: running installers for
	# real is only safe while every write target is mounted, and a missed
	# mount presents as an unreachable line rather than an error. This turns
	# that silent case into a loud one.
	local tree_before
	tree_before="$(cd "$REPO_ROOT" && git status --porcelain)"

	write_case_runner

	# Seeds are created after the mounts, from inside the namespace: a path
	# under a bound target does not exist until that target is mounted.
	{
		local seed
		for seed in ${SEED_DIRS[@]+"${SEED_DIRS[@]}"}; do
			printf 'mkdir -p %q\n' "$seed"
		done
		for seed in ${SEED_FILES[@]+"${SEED_FILES[@]}"}; do
			printf 'mkdir -p %q && : >%q\n' "$(dirname "$seed")" "$seed"
		done
	} >>"$JAIL/mounts.sh"

	# Two passes, two fresh namespaces; they cannot be merged (kcov's ptrace
	# and xtrace are mutually exclusive -- measured: under xtrace every kcov
	# hit collapses to 0). "kcov" gives the line set, "trace" gives the truth
	# about which of those lines ran. See lib/shell_coverage_case_runner.sh.
	local pass
	for pass in kcov trace; do
		unshare --user --map-root-user --mount --fork \
			"$JAIL/run_cases.sh" "$JAIL" "$subject_dir" "$subject_base" \
			"$measure_base" "$CASE_TIMEOUT" "$pass"
	done

	reconcile_pass_failures

	local tree_after
	tree_after="$(cd "$REPO_ROOT" && git status --porcelain)"
	if [[ $tree_before != "$tree_after" ]]; then
		echo "Error: the subject modified the working tree; a write escaped the jail" >&2
		diff <(printf '%s\n' "$tree_before") <(printf '%s\n' "$tree_after") >&2 || true
		exit 1
	fi

	# Report coverage first -- the number is wanted even when a case failed,
	# and suppressing it would hide the diagnosis behind the symptom.
	local report_rc=0
	python3 "$REPO_ROOT/meta/scripts/shell_coverage_report.py" \
		"$JAIL/cov" "$measure_base" "$MIN_PERCENT" "$JAIL/trace" || report_rc=$?

	if [[ $FAIL_ON_CASE_ERROR -eq 1 && -s "$JAIL/case_failures" ]]; then
		printf 'Error: %d case(s) exited non-zero; see the warn: lines above\n' \
			"$(wc -l <"$JAIL/case_failures")" >&2
		return 1
	fi

	return "$report_rc"
}

main "$@"
