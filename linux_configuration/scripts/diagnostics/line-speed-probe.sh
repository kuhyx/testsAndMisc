#!/bin/bash

# ============================================================================
# line-speed-probe.sh — measure burst vs sustained inbound throughput.
#
# Why this exists: a single-stream download tops out around 180 Mbps on this
# line, which reads convincingly as "the ISP shapes us to 180". It does not —
# a many-connection swarm reaches 986 Mbps with zero retransmits. Only a
# multi-stream probe reveals real line capacity, so this script runs both and
# reports them separately.
#
# Baseline captured 2026-07-19 ~17:30 (Sunday evening, European peak):
#     geo.mirror.pkgbuild.com  1 stream   PEAK 493  SUSTAINED 182 Mbps
#     ftp.icm.edu.pl           1 stream   PEAK 308  SUSTAINED 164 Mbps
#     4 mixed mirrors          4 streams  PEAK 766  SUSTAINED 258 Mbps
#
# Downloads are discarded to /dev/null; only the report is written. Rates come
# from the NIC's own counters, so competing traffic is included by design.
#
# Usage:  line-speed-probe.sh [url]     (default: probe the standard set)
# ============================================================================

set -euo pipefail

IFACE="${IFACE:-enp6s0}"
DURATION="${DURATION:-90}"    # seconds per probe
STEP=5                        # sample interval
REPORT_DIR="${REPORT_DIR:-${HOME}/.local/share/line-speed-test}"

MIRROR_PL="https://ftp.icm.edu.pl/pub/Linux/dist/archlinux/iso/latest/archlinux-x86_64.iso"
MIRROR_GEO="https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso"
MIRROR_RACK="https://mirror.rackspace.com/archlinux/iso/latest/archlinux-x86_64.iso"
MIRROR_KERNEL="https://mirrors.edge.kernel.org/archlinux/iso/latest/archlinux-x86_64.iso"

PIDS=()
REPORT=""

# --- pure helpers (unit-tested by linux_configuration/tests) ----------------

bytes_to_mbps() {
    local delta="$1" secs="$2"
    (( secs > 0 )) || { printf '0'; return; }
    printf '%d' $(( delta * 8 / secs / 1000000 ))
}

# Sustained throughput = mean of the SECOND HALF of the samples. The first half
# is discarded deliberately: it contains TCP slow start and any ISP burst
# allowance, both of which inflate the figure we care about.
sustained_of() {
    (( $# > 0 )) || { printf '0'; return; }
    local count=$# half=$(( $# / 2 )) sum=0 i=0 v
    for v in "$@"; do
        i=$(( i + 1 ))
        (( i > half )) && sum=$(( sum + v ))
    done
    printf '%d' $(( sum / (count - half) ))
}

max_of() {
    (( $# > 0 )) || { printf '0'; return; }
    local m=0 v
    for v in "$@"; do (( v > m )) && m=$v; done
    printf '%d' "$m"
}

# Interpret the best sustained figure seen across all probes.
verdict_for() {
    local best="$1"
    if (( best >= 600 )); then
        printf 'LINE_OK'
    elif (( best >= 350 )); then
        printf 'PARTIAL'
    else
        printf 'SLOW'
    fi
}

# --- measurement -----------------------------------------------------------

cleanup() {
    local p
    for p in "${PIDS[@]:-}"; do
        [[ -n "$p" ]] && kill "$p" 2>/dev/null || true
    done
    wait 2>/dev/null || true
}
trap cleanup EXIT

rx_bytes() { cat "/sys/class/net/${IFACE}/statistics/rx_bytes"; }

emit() { printf '%s\n' "$1" | tee -a "$REPORT"; }

# probe <label> <url>...
probe() {
    local label="$1"; shift
    local urls=("$@")
    local t a b mbps
    local -a samples=()

    emit ""
    emit "### ${label} (${#urls[@]} stream(s), ${DURATION}s)"

    PIDS=()
    local u
    for u in "${urls[@]}"; do
        curl -s --max-time "$(( DURATION + 30 ))" -o /dev/null "$u" &
        PIDS+=("$!")
    done

    for (( t = STEP; t <= DURATION; t += STEP )); do
        a=$(rx_bytes); sleep "$STEP"; b=$(rx_bytes)
        mbps=$(bytes_to_mbps $(( b - a )) "$STEP")
        samples+=("$mbps")
        emit "$(printf '  t=%3ds  %5d Mbps' "$t" "$mbps")"
    done

    cleanup
    PIDS=()

    local peak sustained
    peak=$(max_of "${samples[@]}")
    sustained=$(sustained_of "${samples[@]}")
    emit "  --> PEAK ${peak} Mbps | SUSTAINED ${sustained} Mbps"
    printf '%s\t%s\t%s\n' "$label" "$peak" "$sustained" >>"${REPORT}.tsv"
}

main() {
    mkdir -p "$REPORT_DIR"
    REPORT="${REPORT_DIR}/report-$(date +%Y%m%d-%H%M).txt"
    : >"$REPORT"; : >"${REPORT}.tsv"

    emit "# Line speed probe — $(date '+%Y-%m-%d %H:%M:%S %Z')"
    emit "# interface=${IFACE} duration=${DURATION}s"

    if [[ $# -ge 1 ]]; then
        probe "Custom target" "$1"
    else
        probe "PL mirror (icm.edu.pl), single stream" "$MIRROR_PL"
        probe "Geo mirror (pkgbuild), single stream"  "$MIRROR_GEO"
        probe "Four mirrors in parallel" "$MIRROR_PL" "$MIRROR_GEO" \
                                         "$MIRROR_RACK" "$MIRROR_KERNEL"
    fi

    local best
    best=$(awk -F'\t' 'BEGIN{m=0} $3>m{m=$3} END{print m+0}' "${REPORT}.tsv")
    emit ""
    emit "## Verdict"
    emit "Best sustained figure this run: ${best} Mbps"
    case "$(verdict_for "$best")" in
        LINE_OK)
            emit "=> Line is healthy. Any slowness is the download client, not the link."
            emit "   Compare clients with steam-download-duty.sh." ;;
        PARTIAL)
            emit "=> Better than a congested evening but short of gigabit."
            emit "   Re-run off-peak before drawing conclusions." ;;
        *)
            emit "=> Low. Re-run off-peak; if still low, capture a multi-stream figure"
            emit "   before blaming the ISP — single streams under-report badly." ;;
    esac

    ln -sfn "$REPORT" "${REPORT_DIR}/latest.txt"
    emit ""
    emit "Report: ${REPORT}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
