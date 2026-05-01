#!/bin/bash
# Easy entrypoint for system usage reports.
# Usage:
#   ./run.sh                 # today's report to stdout
#   ./run.sh --date 20260501 # specific day
#   ./run.sh --top 25        # override row count
#
# Any args are forwarded to usage_report.py unchanged.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPORT_SCRIPT="$SCRIPT_DIR/linux_configuration/scripts/system-maintenance/bin/usage_report.py"

if [[ ! -f "$REPORT_SCRIPT" ]]; then
    echo "Error: usage_report.py not found at: $REPORT_SCRIPT" >&2
    exit 1
fi

exec python3 "$REPORT_SCRIPT" "$@"
