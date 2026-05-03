#!/bin/bash
# Easy entrypoint for system usage reports and polling script diagnostics.
# Usage:
#   ./run.sh                      # today's report to stdout
#   ./run.sh --date 20260501      # specific day
#   ./run.sh --top 25             # override row count
#   ./run.sh --profile [duration] # profile polling scripts (default 60s)
#   ./run.sh --diagnose           # find inefficient shell scripts
#
# Any other args are forwarded to usage_report.py unchanged.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPORT_SCRIPT="$SCRIPT_DIR/linux_configuration/scripts/system-maintenance/bin/usage_report.py"

if [[ ! -f "$REPORT_SCRIPT" ]]; then
    echo "Error: usage_report.py not found at: $REPORT_SCRIPT" >&2
    exit 1
fi

# Profiling mode: trace fork-heavy scripts over time
profile_polling_scripts() {
    local duration="${1:-60}"
    echo "=== Polling Script Profiler (${duration}s) ===" >&2
    echo "Tracing fork/exec calls in shell scripts..." >&2
    echo "" >&2

    # Find common polling script processes and trace them
    local trace_file="/tmp/polling_trace_$$.txt"

    # Use perf/strace to capture system calls
    (
        timeout "$duration" strace -f -e trace=clone,execve -c -p $$ 2>&1 || true
    ) > "$trace_file" 2>&1

    echo "Trace completed. Analyzing results:" >&2
    echo "" >&2

    # Show fork/exec heavy processes
    if ! grep -e "execve" -e "clone" "$trace_file" | head -20; then
        :
    fi

    rm -f "$trace_file"
}

# Diagnostic mode: find inefficient patterns in shell scripts
diagnose_polling_scripts() {
    echo "=== Shell Script Efficiency Audit ===" >&2
    echo "" >&2

    local issues_found=0

    # Check for common anti-patterns
    echo "Checking for anti-patterns in shell scripts..." >&2
    echo "" >&2

    # Pattern 1: while true with sleep (no event-driven check)
    echo "1. Polling loops (while true + sleep):" >&2
    set +e
    grep -r "while true\|while :" --include="*.sh" "$SCRIPT_DIR" 2>/dev/null \
        | grep -v "Binary" | grep -v ".git" | head -5
    set -e
    issues_found=$((issues_found + 1))
    echo "" >&2

    # Pattern 2: $(date +...) calls in loops (fork-heavy)
    echo "2. Excessive date calls (each forks a process):" >&2
    set +e
    grep -r '\$(date' --include="*.sh" "$SCRIPT_DIR" 2>/dev/null \
        | grep -v "Binary" | grep -v ".git" | head -5
    set -e
    issues_found=$((issues_found + 1))
    echo "" >&2

    # Pattern 3: pgrep/xdotool in loops
    echo "3. Process inspection in loops (pgrep, xdotool):" >&2
    set +e
    grep -r "while.*pgrep\|while.*xdotool\|pgrep.*while" --include="*.sh" "$SCRIPT_DIR" 2>/dev/null \
        | grep -v "Binary" | grep -v ".git" | head -5
    set -e
    issues_found=$((issues_found + 1))
    echo "" >&2

    # Pattern 4: pipes in hot paths
    echo "4. Heavy pipes in polling scripts (| awk, | grep, | tr):" >&2
    set +e
    while_true_file_list="$(mktemp)"
    heavy_pipe_matches="$(mktemp)"
    grep -r "while true" --include="*.sh" "$SCRIPT_DIR" > "$while_true_file_list" 2>/dev/null
    if [ -s "$while_true_file_list" ]; then
        xargs grep -l -e " | awk" -e " | grep" -e " | tr" < "$while_true_file_list" > "$heavy_pipe_matches" 2>/dev/null
        head -5 "$heavy_pipe_matches"
    fi
    rm -f "$while_true_file_list" "$heavy_pipe_matches"
    set -e
    issues_found=$((issues_found + 1))
    echo "" >&2

    # Pattern 5: sleep with very short intervals
    echo "5. Aggressive polling (sleep < 1s):" >&2
    set +e
    grep -rE "sleep 0\.[0-9]|sleep 0[^0-9]" --include="*.sh" "$SCRIPT_DIR" 2>/dev/null \
        | grep -v "Binary" | grep -v ".git" | head -5
    set -e
    issues_found=$((issues_found + 1))
    echo "" >&2

    echo "=== Recommendations ===" >&2
    echo "1. Replace 'while true + sleep' with event-driven I/O (inotifywait, read -t, etc.)" >&2
    echo "2. Use /proc and /sys instead of forking date, sensors, acpi, etc." >&2
    echo "3. Cache frequently accessed values (e.g., in /tmp state files)" >&2
    echo "4. Use bash builtins: printf %()T instead of date, \${var//} instead of tr, etc." >&2
    echo "5. Use i3blocks interval=persist + event loop instead of polling mode" >&2
    echo "6. Increase polling intervals: 1s → 5s → 10s where acceptable" >&2
}

# Handle special modes
case "${1:-}" in
    --profile)
        profile_polling_scripts "${2:-60}"
        exit 0
        ;;
    --diagnose)
        diagnose_polling_scripts
        exit 0
        ;;
    --help)
        grep '^# Usage:' "$0" | sed 's/^# //' | head -1
        grep '^#   ' "$0" | sed 's/^#   /  /'
        exit 0
        ;;
esac

# Default: run usage_report.py with all remaining args
exec python3 "$REPORT_SCRIPT" "$@"
