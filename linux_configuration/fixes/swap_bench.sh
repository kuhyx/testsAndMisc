#!/bin/bash
# Seeded memory-pressure benchmark for the zram-vs-zswap A/B test.
#
#   swap_bench.sh run host [--seed N] [--size-mib M]   # on kuhy's desktop
#   swap_bench.sh run vm   [--seed N] [--size-mib M]   # inside a vmbox guest
#   swap_bench.sh summary [TSV]                        # medians + winner
#
# One run per call, each under 60 s, appending one row to the results TSV.
# Host mode confines the pressure to a transient scope (RAM capped, swap
# allowed), so only the bench swaps and the desktop keeps its memory; its
# PSI and zswap counters are the scope's own. VM mode puts the whole guest
# under pressure and uses global counters. A run that fails or times out
# records nothing. The Python side (python_pkg/swap_bench) holds the
# workload, the parsing and the winner rule; this script only places it.
# Method and results: DOCS-zswap-vs-zram.md.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SRC_DIR}/../.." && pwd)"
readonly SRC_DIR REPO_ROOT
readonly RESULTS="${SWAP_BENCH_RESULTS:-${SRC_DIR}/swap-bench-results.tsv}"
readonly PROC_VMSTAT="${PROC_VMSTAT:-/proc/vmstat}"
readonly PROC_PRESSURE="${PROC_PRESSURE:-/proc/pressure/memory}"
readonly PROC_MEMINFO="${PROC_MEMINFO:-/proc/meminfo}"
readonly PROC_SELF_CGROUP="${PROC_SELF_CGROUP:-/proc/self/cgroup}"
readonly CGROUP_ROOT="${CGROUP_ROOT:-/sys/fs/cgroup}"
readonly ZRAM_SYSFS="${ZRAM_SYSFS:-/sys/block/zram0}"
readonly ZSWAP_PARAMS_DIR="${ZSWAP_PARAMS_DIR:-/sys/module/zswap/parameters}"
readonly HOST_MEMORY_MAX="${SWAP_BENCH_MEMORY_MAX:-4G}"
# A wrapper on PATH may add properties a scope refuses (Nice=); point this at
# /usr/bin/systemd-run to bypass it.
readonly SYSTEMD_RUN="${SWAP_BENCH_SYSTEMD_RUN:-systemd-run}"
readonly DEFAULT_SEED=20261127
readonly DEFAULT_HOST_MIB=6144
readonly DEFAULT_VM_MIB=4608
readonly WORKLOAD_TIMEOUT=50 # scope RuntimeMaxSec=55 is the backstop

die() {
	echo "swap_bench: $*" >&2
	exit 1
}

usage() {
	sed -n '4,6s/^# \{0,1\}//p' "${BASH_SOURCE[0]}" >&2
	exit 2
}

py() { PYTHONPATH="$REPO_ROOT" python3 -m python_pkg.swap_bench "$@"; }

detect_setup() {
	local zram=0 zswap=0
	swapon --noheadings --show=NAME | grep -qx /dev/zram0 && zram=1
	[[ $(cat "${ZSWAP_PARAMS_DIR}/enabled") == Y ]] && zswap=1
	((zram && zswap)) && die "zram0 is swap AND zswap is on: pages are compressed twice; run setup_zram.sh or setup_zswap.sh"
	((zram)) && echo zram && return 0
	((zswap)) && echo zswap && return 0
	die "neither zram nor zswap is active"
}

# snap DIR — copy the global counters one run is measured against, plus
# the PSI of every login session scope: that is the desktop (i3 and what it
# launched), which the host bench scope is not part of.
snap() {
	mkdir -p "$1"
	cp "$PROC_VMSTAT" "$1/vmstat"
	cp "$PROC_PRESSURE" "$1/pressure"
	local -a sessions=("${CGROUP_ROOT}"/user.slice/user-*.slice/session-*.scope/memory.pressure)
	[[ -e ${sessions[0]} ]] && cat "${sessions[@]}" >"$1/desktop_pressure"
	if [[ -e ${ZRAM_SYSFS}/mm_stat ]]; then
		cp "${ZRAM_SYSFS}/mm_stat" "$1/mm_stat"
		cp "${ZRAM_SYSFS}/stat" "$1/zram_stat"
	fi
}

# host_has_room — 0 when MemAvailable covers the scope's RAM cap plus 2 GiB,
# so pressing the scope cannot push the desktop itself into swap.
host_has_room() {
	local cap_kib avail_kib
	cap_kib=$(($(numfmt --from=iec "$HOST_MEMORY_MAX") / 1024))
	avail_kib=$(awk '/^MemAvailable:/ {print $2}' "$PROC_MEMINFO")
	((avail_kib >= cap_kib + 2 * 1024 * 1024))
}

global_full_avg10() { awk '/^full/ {sub("avg10=", "", $2); print $2}' "$PROC_PRESSURE"; }

# inner DIR ENV SIZE SEED — runs inside the scope (host) or the guest (vm).
inner() {
	local dir="$1" env="$2" size="$3" seed="$4" cg
	cg="${CGROUP_ROOT}$(sed -n 's/^0:://p' "$PROC_SELF_CGROUP")"
	local -a snaps=(--snapshot "${PROC_MEMINFO}=${dir}/peak/meminfo")
	[[ $env == host ]] && snaps+=(--snapshot "${cg}/memory.stat=${dir}/peak/memory.stat")
	[[ -e ${ZRAM_SYSFS}/mm_stat ]] && snaps+=(--snapshot "${ZRAM_SYSFS}/mm_stat=${dir}/peak/mm_stat")
	timeout "$WORKLOAD_TIMEOUT" env PYTHONPATH="$REPO_ROOT" python3 -m python_pkg.swap_bench \
		run --size-mib "$size" --seed "$seed" "${snaps[@]}" >"${dir}/workload.txt"
	if [[ $env == host ]]; then
		cp "${cg}/memory.pressure" "${dir}/cg_pressure"
		cp "${cg}/memory.stat" "${dir}/cg_memory.stat"
	fi
}

cmd_run() {
	local env="${1:-}" seed="$DEFAULT_SEED" size=""
	[[ $env == host || $env == vm ]] || usage
	shift
	while (($#)); do
		case "$1" in
		--seed) seed="$2" ;;
		--size-mib) size="$2" ;;
		*) usage ;;
		esac
		shift 2
	done
	[[ -n $size ]] || { [[ $env == host ]] && size=$DEFAULT_HOST_MIB || size=$DEFAULT_VM_MIB; }
	local setup dir rc=0
	setup="$(detect_setup)"
	[[ $env == vm ]] || host_has_room ||
		die "MemAvailable is below ${HOST_MEMORY_MAX} + 2G: a host run now would press the desktop too"
	dir="$(mktemp -d)"
	RUN_DIR="$dir" # global: the EXIT trap runs after this function's locals are gone
	trap 'rm -rf "${RUN_DIR:?}"' EXIT
	echo "global memory PSI full avg10 before: $(global_full_avg10)"
	snap "${dir}/before"
	if [[ $env == host ]]; then
		"$SYSTEMD_RUN" --user --scope --quiet --unit="swap-bench-$$" \
			-p MemoryMax="$HOST_MEMORY_MAX" -p MemorySwapMax=infinity -p RuntimeMaxSec=55 \
			-- bash "${BASH_SOURCE[0]}" _inner "$dir" "$env" "$size" "$seed" || rc=$?
	else
		bash "${BASH_SOURCE[0]}" _inner "$dir" "$env" "$size" "$seed" || rc=$?
	fi
	((rc == 0)) || die "workload failed (exit $rc): no row recorded"
	snap "${dir}/after"
	echo "global memory PSI full avg10 after:  $(global_full_avg10)"
	local -a header=()
	[[ -s $RESULTS ]] || header=(--header)
	py row --dir "$dir" --env "$env" --setup "$setup" --seed "$seed" --size-mib "$size" \
		--date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${header[@]}" | tee -a "$RESULTS"
}

main() {
	case "${1:-}" in
	run) cmd_run "${@:2}" ;;
	summary) py summary "${2:-$RESULTS}" ;;
	_inner) inner "${@:2}" ;;
	*) usage ;;
	esac
}

main "$@"
exit $?
