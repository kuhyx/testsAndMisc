#!/usr/bin/env bash
# Build and demo atop_agg on today's atop log.
set -euo pipefail
cd "$(dirname "$0")"
make
LOG="${1:-/var/log/atop/atop_$(date +%Y%m%d)}"
if [[ ! -f "$LOG" ]]; then
    echo "No atop log at $LOG; pass a path as arg 1." >&2
    exit 1
fi
echo "Aggregating $LOG ..." >&2
atop -r "$LOG" -P PRC,PRM | ./atop_agg | head -20
