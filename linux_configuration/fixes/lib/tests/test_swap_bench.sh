#!/usr/bin/env bash
# lib/tests/test_swap_bench.sh — swap_bench.sh runs the seeded workload in
# the right place, records one row per run, and never records a failed run.
#
# /proc, /sys and the cgroup tree are fixture files; systemd-run is a stub
# that drops its options and runs the command, so no scope and no memory
# pressure is created. The workload itself is the real Python at 1 MiB.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXES_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# shellcheck source=lib_test_core.sh
. "${SCRIPT_DIR}/lib_test_core.sh"

BENCH="${FIXES_DIR}/swap_bench.sh"
readonly BENCH
export SWAP_BENCH_RESULTS="${TEST_TMPDIR}/results.tsv"
export PROC_VMSTAT="${TEST_TMPDIR}/proc/vmstat"
export PROC_PRESSURE="${TEST_TMPDIR}/proc/pressure_memory"
export PROC_MEMINFO="${TEST_TMPDIR}/proc/meminfo"
export PROC_SELF_CGROUP="${TEST_TMPDIR}/proc/self_cgroup"
export CGROUP_ROOT="${TEST_TMPDIR}/cgroup"
export ZRAM_SYSFS="${TEST_TMPDIR}/sys/block/zram0"
export ZSWAP_PARAMS_DIR="${TEST_TMPDIR}/sys/module/zswap/parameters"
mkdir -p "${TEST_TMPDIR}/proc" "${CGROUP_ROOT}/bench.scope" "$ZRAM_SYSFS" "$ZSWAP_PARAMS_DIR"
psi='some avg10=0.00 avg60=0.00 avg300=0.00 total=5000
full avg10=0.00 avg60=0.00 avg300=0.00 total=2000'
printf '%s\n' "$psi" >"$PROC_PRESSURE"
printf '%s\n' "$psi" >"${CGROUP_ROOT}/bench.scope/memory.pressure"
mkdir -p "${CGROUP_ROOT}/user.slice/user-1000.slice/session-1.scope"
printf '%s\n' "$psi" >"${CGROUP_ROOT}/user.slice/user-1000.slice/session-1.scope/memory.pressure"
printf 'zswap 0\nzswapped 0\nzswpwb 0\n' >"${CGROUP_ROOT}/bench.scope/memory.stat"
printf 'pswpout 10\nzswpwb 0\n' >"$PROC_VMSTAT"
printf 'MemAvailable: 9000000 kB\nZswap: 0 kB\nZswapped: 0 kB\n' >"$PROC_MEMINFO"
printf '0::/bench.scope\n' >"$PROC_SELF_CGROUP"
printf '1 0 0 0 1 0 80 0 0 0 0\n' >"${ZRAM_SYSFS}/stat"
printf '4096 1024 0 0\n' >"${ZRAM_SYSFS}/mm_stat"

# BUMP_DESKTOP_FULL_US: stall the login session by this much during the run.
_t_stub_stdin systemd-run <<'STUB'
while [[ $1 != -- ]]; do shift; done
shift
"$@" || exit $?
if [[ -n ${BUMP_DESKTOP_FULL_US:-} ]]; then
	printf 'some avg10=0.00 avg60=0.00 avg300=0.00 total=5000\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=%s\n' \
		"$((2000 + BUMP_DESKTOP_FULL_US))" >"${CGROUP_ROOT}/user.slice/user-1000.slice/session-1.scope/memory.pressure"
fi
STUB
_t_stub_cat swapon swaps
_setup() { # _setup zram|zswap|none|both
	case "$1" in
	zram | both) printf '/swapfile\n/dev/zram0\n' >"${DEV}/swaps" ;;
	*) printf '/swapfile\n' >"${DEV}/swaps" ;;
	esac
	case "$1" in zswap | both) echo Y ;; *) echo N ;; esac >"${ZSWAP_PARAMS_DIR}/enabled"
	_t_reset_calls
}
_col() { awk -F'\t' -v c="$1" 'NR==1 {for (i=1;i<=NF;i++) if ($i==c) n=i; next} {print $n}' "$SWAP_BENCH_RESULTS"; }

echo "host run under a swap-allowed scope (C6)"
_setup zram
_t_run bash "$BENCH" run host --seed 7 --size-mib 1
_t_eq 0 "$?" "run host: exits 0"
_t_contains "$(_t_calls)" "MemoryMax=4G" "run host: scope caps RAM at 4G"
_t_contains "$(_t_calls)" "MemorySwapMax=infinity" "run host: scope may swap"
_t_contains "$(_t_calls)" "RuntimeMaxSec=55" "run host: scope dies before the 60 s cap"
_t_eq "zram" "$(_col setup)" "run host: row records the zram setup"
_t_eq "host" "$(_col env)" "run host: row records env"
_t_eq 0 "$(_col outside_pswpout)" "run host: records other processes' swap-outs"

echo "host run that stalls the desktop fails loudly (C6)"
rows_before=$(wc -l <"$SWAP_BENCH_RESULTS")
BUMP_DESKTOP_FULL_US=2000000 _t_run bash "$BENCH" run host --seed 7 --size-mib 1
_t_eq 3 "$?" "pressed desktop: exits 3"
_t_contains "$out" "the login sessions stalled 2000 ms (limit 1000 ms)" "pressed desktop: names the stall"
_t_eq "$((rows_before + 1))" "$(wc -l <"$SWAP_BENCH_RESULTS")" "pressed desktop: the row is still recorded"
sed -i '$d' "$SWAP_BENCH_RESULTS"
printf '%s\n' "$psi" >"${CGROUP_ROOT}/user.slice/user-1000.slice/session-1.scope/memory.pressure"
_t_eq 0 "$(_col desktop_full_ms)" "run host: records the session scopes' PSI stall"

echo "same seed, same workload (C7)"
_t_run bash "$BENCH" run host --seed 7 --size-mib 1
_t_eq 1 "$(grep -c '^date' "$SWAP_BENCH_RESULTS")" "rerun: header written once"
_t_eq 1 "$(_col fill_crc | sort -u | wc -l)" "rerun: same fill checksum"
_t_eq 1 "$(_col touch_crc | sort -u | wc -l)" "rerun: same touch checksum"
_t_eq 256 "$(_col pages | sort -u)" "rerun: same page count"

echo "vm run is system-wide, no scope"
_setup zswap
_t_run bash "$BENCH" run vm --seed 7 --size-mib 1
_t_eq 0 "$?" "run vm: exits 0"
_t_lacks "$(_t_calls)" "systemd-run" "run vm: no scope"
_t_eq zswap "$(_col setup | tail -1)" "run vm: row records zswap"

echo "refusals record nothing"
rows="$(wc -l <"$SWAP_BENCH_RESULTS")"
_setup none
_t_run bash "$BENCH" run host --size-mib 1
_t_eq 1 "$?" "neither setup: exit 1"
_t_contains "$out" "neither zram nor zswap" "neither setup: says so"
_setup both
_t_run bash "$BENCH" run host --size-mib 1
_t_eq 1 "$?" "both setups: exit 1"
_setup zram
_t_run bash "$BENCH" run host --size-mib 0
_t_eq 1 "$?" "failed workload: exit 1"
_t_contains "$out" "no row recorded" "failed workload: says no row"
printf 'MemAvailable: 6000000 kB\n' >"$PROC_MEMINFO"
_t_run bash "$BENCH" run host --size-mib 1
_t_eq 1 "$?" "low MemAvailable: host run refused"
_t_contains "$out" "press the desktop" "low MemAvailable: says why"
printf 'MemAvailable: 9000000 kB\nZswap: 0 kB\nZswapped: 0 kB\n' >"$PROC_MEMINFO"
_t_run bash "$BENCH" run cloud
_t_eq 2 "$?" "unknown env: usage exit 2"
_t_eq "$rows" "$(wc -l <"$SWAP_BENCH_RESULTS")" "refusals: no row appended"

echo "summary (C8)"
_t_run bash "$BENCH" summary
_t_eq 0 "$?" "summary: exits 0"
_t_contains "$out" "| host | zram | 2 |" "summary: host zram medians over 2 runs"
_t_contains "$out" "vm winner: n/a" "summary: no vm winner without both setups"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
