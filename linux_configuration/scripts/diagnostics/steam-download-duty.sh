#!/bin/bash

# ============================================================================
# steam-download-duty.sh — measure a download's DUTY CYCLE, not its average.
#
# Why this exists: on this machine the link is not bandwidth-limited, but the
# Steam client is. Sampling at 1 s shows Steam alternating between
# multi-hundred-Mbps bursts and multi-second stalls in which it uses ~1% CPU,
# no disk, and transmits only keepalives. Any averaged "Mbps" figure is really
#   burst_rate x duty_cycle
# and hides which of the two factors is actually wrong.
#
# Measured 2026-07-19 (see the diagnosis writeup): Steam client 38% duty /
# ~170 Mbps effective, vs depotdownloader -max-downloads 32 at 97% duty /
# 696 Mbps effective on the same line, same CDN, same minute.
#
# Use this to compare download clients or regions objectively — the Steam UI's
# averaged number cannot distinguish "slow link" from "idle client".
#
# Usage:  steam-download-duty.sh [seconds]      (default 60)
# ============================================================================

set -euo pipefail

IFACE="${IFACE:-enp6s0}"
IDLE_THRESHOLD_MBPS="${IDLE_THRESHOLD_MBPS:-20}"  # below this = stalled second

# --- pure helpers (unit-tested by linux_configuration/tests) ----------------

# Convert a byte delta observed over N seconds into Mbps (integer).
bytes_to_mbps() {
    local delta="$1" secs="$2"
    (( secs > 0 )) || { printf '0'; return; }
    printf '%d' $(( delta * 8 / secs / 1000000 ))
}

# Percentage of sampled seconds that carried traffic.
duty_pct() {
    local active="$1" total="$2"
    (( total > 0 )) || { printf '0'; return; }
    printf '%d' $(( active * 100 / total ))
}

# Integer mean of the numeric arguments (0 when given none).
mean_of() {
    (( $# > 0 )) || { printf '0'; return; }
    local sum=0 v
    for v in "$@"; do sum=$(( sum + v )); done
    printf '%d' $(( sum / $# ))
}

# Classify a run. Kept separate from printing so it can be asserted on.
#   LINK_LIMITED           - transferring almost always; the rate is the rate
#   CLIENT_IDLE            - fast when active but idle a lot => client's fault
#   MIXED                  - neither clean bursts nor high duty
classify() {
    local duty="$1" burst="$2"
    if (( duty >= 80 )); then
        printf 'LINK_LIMITED'
    elif (( burst >= 400 )); then
        printf 'CLIENT_IDLE'
    else
        printf 'MIXED'
    fi
}

# --- measurement -----------------------------------------------------------

rx_bytes() { cat "/sys/class/net/${IFACE}/statistics/rx_bytes"; }

main() {
    local total="${1:-60}"
    local prev cur mbps active=0 peak=0
    local -a samples=() active_samples=() trace=()

    printf 'Sampling %ss at 1s resolution on %s ...\n\n' "$total" "$IFACE"
    prev=$(rx_bytes)

    local i
    for (( i = 1; i <= total; i++ )); do
        sleep 1
        cur=$(rx_bytes)
        mbps=$(bytes_to_mbps $(( cur - prev )) 1)
        prev=$cur
        samples+=("$mbps")
        if (( mbps > peak )); then peak=$mbps; fi

        if (( mbps >= IDLE_THRESHOLD_MBPS )); then
            active=$(( active + 1 )); active_samples+=("$mbps"); trace+=("#")
        else
            trace+=(".")
        fi
    done

    printf 'pattern (# = transferring, . = stalled):\n  '
    printf '%s' "${trace[@]}"
    printf '\n\n'

    local duty burst overall
    duty=$(duty_pct "$active" "$total")
    burst=$(mean_of ${active_samples[@]+"${active_samples[@]}"})
    overall=$(mean_of ${samples[@]+"${samples[@]}"})

    printf 'duty cycle      : %d%%  (%ds transferring / %ds stalled)\n' \
        "$duty" "$active" "$(( total - active ))"
    printf 'rate when active: %d Mbps (peak %d)\n' "$burst" "$peak"
    printf 'effective avg   : %d Mbps\n\n' "$overall"

    case "$(classify "$duty" "$burst")" in
        LINK_LIMITED)
            printf 'VERDICT: link is the limit — %d Mbps is close to what you get.\n' "$burst" ;;
        CLIENT_IDLE)
            printf 'VERDICT: NOT bandwidth-limited. Bursts reach %d Mbps but the\n' "$burst"
            printf '         transfer is idle %d%% of the time. At 100%% duty this\n' "$(( 100 - duty ))"
            printf '         link would give ~%d Mbps. Compare clients/regions by\n' "$burst"
            printf '         duty cycle, not by the averaged UI number.\n' ;;
        *)
            printf 'VERDICT: mixed — bursts only reach %d Mbps and duty is %d%%.\n' \
                "$burst" "$duty" ;;
    esac
}

# Only run when executed directly, so tests can source the helpers above.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
