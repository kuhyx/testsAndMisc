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
#      28.95%, because the wrapper sources its sibling libs from there and
#      took its "libraries missing" escape hatch. An over-aggressive mount
#      looks exactly like unreachable code.
#
# Entry scripts must be executed in place: they resolve their libs via
# BASH_SOURCE and common.sh via `readlink -f "$0"`, so staging a copy into a
# temp dir (which works fine for a sourced lib) breaks them.
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
  --min <percent>    fail below this (default 100)
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
	--min)
		MIN_PERCENT="$2"
		shift 2
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

	# The runner below executes INSIDE the namespace, so it is written out as
	# its own file rather than inlined: a quoted inline block would have to
	# defer every expansion to the child shell, which reads as a quoting bug
	# and trips SC2016.
	cat >"$JAIL/run_cases.sh" <<'INNER'
#!/usr/bin/env bash
set -u
jail="$1"
subject_dir="$2"
subject_base="$3"
measure_base="$4"
. "$jail/mounts.sh"
export PATH="$jail/bin:/usr/bin:/bin"
export HOME="$jail/home"
USER="${USER:-root}"
export USER
export SUDO_USER="$USER"
cd "$subject_dir" || exit 1
while IFS= read -r line; do
    read -r -a case_args <<<"$line"
    kcov --include-pattern="$measure_base" "$jail/cov" \
        "./$subject_base" ${case_args[@]+"${case_args[@]}"} \
        >/dev/null 2>&1 || true
done <"$jail/cases"
INNER
	chmod +x "$JAIL/run_cases.sh"

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

	unshare --user --map-root-user --mount --fork \
		"$JAIL/run_cases.sh" "$JAIL" "$subject_dir" "$subject_base" "$measure_base"

	local tree_after
	tree_after="$(cd "$REPO_ROOT" && git status --porcelain)"
	if [[ $tree_before != "$tree_after" ]]; then
		echo "Error: the subject modified the working tree; a write escaped the jail" >&2
		diff <(printf '%s\n' "$tree_before") <(printf '%s\n' "$tree_after") >&2 || true
		exit 1
	fi

	python3 "$REPO_ROOT/meta/scripts/shell_coverage_report.py" \
		"$JAIL/cov" "$measure_base" "$MIN_PERCENT"
}

main "$@"
