#!/usr/bin/env bash
# lib/tests/pacman_hook_stall_entry_harness.sh — shared setup for the entry
# script's subprocess tests: fake pacman.orig/ps/journalctl/pgrep/logger on
# PATH, and the run_entry helper that drives diagnose_pacman_hook_stall.sh
# under unshare -r.
#
# Sourced, not executed, by test_diagnose_pacman_hook_stall_*.sh files.
#
# Deliberately does NOT put a fake `sleep` on PATH: run_one's `while kill -0`
# loop compares real epoch timestamps, so a fake sleep that returns instantly
# turns it into a tight spin loop. Real sleep + small STALL_TIMEOUT/
# HARD_TIMEOUT values keep tests fast while exercising the real timing logic.
set -uo pipefail

if ! command -v unshare >/dev/null 2>&1 || ! unshare -r true 2>/dev/null; then
	echo "SKIP: unshare -r not available in this environment" >&2
	exit 0
fi

PASS=0
FAIL=0
_t_pass() {
	PASS=$((PASS + 1))
	printf '  OK: %s\n' "$1"
}
_t_fail() {
	FAIL=$((FAIL + 1))
	printf '  FAIL: %s\n' "$1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENTRY="${FIXES_DIR}/diagnose_pacman_hook_stall.sh"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

FAKE_BIN="${TMPDIR}/fake_bin"
mkdir -p "$FAKE_BIN"

# pacman.orig: -Q reports an installed version; -U hangs for
# $DEV/hang_seconds (default 0), appending a pacman.log line partway through
# if $DEV/log_advance_at is set, then exits (or dies cleanly on TERM/INT so
# the hard-timeout/SIGTERM tests don't leave an orphan).
cat >"${FAKE_BIN}/pacman.orig" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
DEV="${STALL_ENTRY_TEST_DEV}"
printf '%s\n' "pacman.orig $*" >>"${DEV}/calls"
if [[ "$1" == "-Q" ]]; then
	printf '%s %s\n' "$2" "1.0.0-1"
	exit 0
fi
if [[ "$1" == "-U" ]]; then
	hang=0
	[[ -f "${DEV}/hang_seconds" ]] && hang="$(cat "${DEV}/hang_seconds")"
	trap 'exit 0' TERM INT
	if [[ -f "${DEV}/log_advance_at" ]]; then
		sleep "$(cat "${DEV}/log_advance_at")"
		echo "running 'some.hook'..." >>"${PACMAN_LOG}"
		hang=$((hang - $(cat "${DEV}/log_advance_at")))
		((hang < 0)) && hang=0
	fi
	sleep "$hang"
	exit 0
fi
exit 0
EOF
chmod +x "${FAKE_BIN}/pacman.orig"

for tool in ps journalctl pgrep logger; do
	cat >"${FAKE_BIN}/${tool}" <<EOF
#!/usr/bin/env bash
printf '%s\n' "${tool} \$*" >>"\${STALL_ENTRY_TEST_DEV}/calls"
exit 0
EOF
	chmod +x "${FAKE_BIN}/${tool}"
done

export PATH="${FAKE_BIN}:${PATH}"
export PACMAN_BIN="${FAKE_BIN}/pacman.orig"
export CACHE_DIR="${TMPDIR}/cache"
export PACMAN_LOCK="${TMPDIR}/db.lck"
# Matches the fake pacman.orig's `-Q base-devel` -> "base-devel 1.0.0-1".
mkdir -p "$CACHE_DIR"
touch "${CACHE_DIR}/base-devel-1.0.0-1-x86_64.pkg.tar.zst"
# Also cache the package the -p/--package test overrides to.
touch "${CACHE_DIR}/some-other-pkg-1.0.0-1-x86_64.pkg.tar.zst"

# run_entry [--hang N] [--log-advance-at N] [--background] ARGS... — runs the
# entry script under unshare -r with a fresh PACMAN_LOG/OUT_DIR/DEV, waits up
# to 15s (or runs detached if --background is given), and returns the run's
# directory (stdout/stderr/rc/dev/pacman.log/dumps all live under it).
run_entry() {
	local hang=0 log_advance_at="" background=0
	local parsing_helper_flags=1
	while ((parsing_helper_flags == 1)) && [[ "$1" == --* ]]; do
		case "$1" in
		--hang)
			hang="$2"
			shift 2
			;;
		--log-advance-at)
			log_advance_at="$2"
			shift 2
			;;
		--background)
			background=1
			shift
			;;
		*)
			# Not one of this helper's own flags -- it's a real argument
			# for the entry script (e.g. --nope, --with-load, --watch).
			parsing_helper_flags=0
			;;
		esac
	done

	local out_dir="${TMPDIR}/run_$$_${RANDOM}"
	mkdir -p "$out_dir"
	local dev="${out_dir}/dev"
	mkdir -p "$dev"
	: >"${dev}/calls"
	echo "$hang" >"${dev}/hang_seconds"
	[[ -n "$log_advance_at" ]] && echo "$log_advance_at" >"${dev}/log_advance_at"
	local pacman_log="${out_dir}/pacman.log"
	: >"$pacman_log"
	local run_out_dir="${out_dir}/dumps"

	if ((background == 1)); then
		STALL_ENTRY_TEST_DEV="$dev" PACMAN_LOG="$pacman_log" \
			unshare -r bash "$ENTRY" -o "$run_out_dir" "$@" \
			>"${out_dir}/stdout" 2>"${out_dir}/stderr" &
		echo "$!" >"${out_dir}/pid"
	else
		STALL_ENTRY_TEST_DEV="$dev" PACMAN_LOG="$pacman_log" \
			timeout 15 unshare -r bash "$ENTRY" -o "$run_out_dir" "$@" \
			>"${out_dir}/stdout" 2>"${out_dir}/stderr"
		echo "$?" >"${out_dir}/rc"
	fi
	printf '%s' "$out_dir"
}
