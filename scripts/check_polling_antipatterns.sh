#!/bin/bash
# Pre-commit hook to detect polling script anti-patterns.
# Blocks commits of shell scripts that violate efficient polling best practices.
#
# Usage: check_polling_antipatterns.sh [files...]
# Exit codes: 0 = no issues, 1 = issues found

set -euo pipefail

errors=0
files_checked=0

# Patterns to detect (these are red flags for fork storms)
# shellcheck disable=SC2034
declare -A patterns=(
    ['while_true_with_sleep']='while\s+(true|:).*sleep'
    ['date_in_loop']='while.*date|for.*date'
    ['pgrep_in_loop']='while.*pgrep|for.*pgrep'
    ['xdotool_in_loop']='while.*xdotool|for.*xdotool'
    ['pipe_fork_chain']='|.*|.*|.*|'
    ['subshell_date']='$\(date\s+\+'
    ['backtick_date']='`date\s+\+'
    ['excessive_fork_chain']='(\$\(.*\|.*\|.*\)|`.*\|.*\|`)'
    ['sleep_less_than_one']='sleep\s+0\.[0-9]'
)

usage() {
    echo "Usage: $(basename "$0") [files...]"
    echo ""
    echo "Checks shell scripts for polling anti-patterns that cause fork storms."
    echo "Exit code 0 = no issues, 1 = issues found"
    echo ""
    echo "Patterns detected:"
    echo "  - while true + sleep (should use event-driven I/O)"
    echo "  - \$(date +...) in loops (forks process)"
    echo "  - pgrep/xdotool in loops (forks process)"
    echo "  - Multiple piped commands (each | forks)"
    echo "  - Aggressive polling (sleep < 1s)"
    exit 0
}

check_file() {
    local file="$1"

    # Skip non-shell files
    if ! grep -qE '^#!.*/(ba)?sh' "$file" 2>/dev/null; then
        return 0
    fi

    files_checked=$((files_checked + 1))

    # Single-pass awk analysis: C code, no bash loops, no per-line subshell forks.
    # '\'' embeds a literal single quote inside a bash single-quoted string.
    local findings
    findings=$(awk '
        /^[[:space:]]*([a-zA-Z0-9_]*_(loop|daemon)|poll[a-zA-Z0-9_]*)[[:space:]]*\(\)/ { in_poll=1 }
        /^[[:space:]]*\}/ { in_poll=0 }
        in_poll {
            if (/while[[:space:]]+(true|:)/ && /sleep/)
                print NR ": while true/: + sleep (use event-driven I/O)"
            if (/\$\(date[[:space:]]/ || /`date[[:space:]]/)
                print NR ": date fork in polling function"
            if (/[^_a-zA-Z0-9]pgrep/ || /^[[:space:]]*pgrep/)
                print NR ": pgrep in polling context"
            if (/[^_a-zA-Z0-9]xdotool/ || /^[[:space:]]*xdotool/)
                print NR ": xdotool in polling context"
            if (/sleep[[:space:]]+0\.[0-9]/)
                print NR ": Aggressive polling (sleep < 1s)"
        }
        !/^[[:space:]]*#/ && !/=/ && !/\)[[:space:]]*(#.*)?$/ && !/;;/ {
            line = $0
            gsub(/\|\|/, "", line)
            while (match(line, /'\''[^'\'']*'\''/)) line = substr(line, 1, RSTART-1) substr(line, RSTART+RLENGTH)
            while (match(line, /"[^"]*"/)) line = substr(line, 1, RSTART-1) substr(line, RSTART+RLENGTH)
            n = gsub(/\|/, "", line)
            if (n > 3) print NR ": Excessive pipes (" n " pipes = many forks)"
        }
    ' "$file")

    if [[ -n "$findings" ]]; then
        echo "  $file:"
        while IFS= read -r finding; do
            echo "    Line $finding"
        done <<< "$findings"
        errors=$((errors + 1))
        return 1
    fi
    return 0
}
provide_suggestions() {
    echo ""
    echo "📋 Optimization Tips:"
    echo ""
    echo "Replace polling loops with:"
    echo "  • inotifywait/fanotify for file system events"
    echo "  • timerfd for interval-based tasks"
    echo "  • select/poll for I/O multiplexing"
    echo "  • systemd timers for scheduled tasks"
    echo "  • dbus signals for system events"
    echo ""
    echo "Reduce fork overhead:"
    echo "  • Cache \$(date +%s) in variable, update periodically"
    echo "  • Use /proc filesystem instead of pgrep"
    echo "  • Consolidate commands with && instead of separate invocations"
    echo ""
}

main() {
    # Show usage if requested
    [[ "$#" -eq 0 || "$1" == "-h" || "$1" == "--help" ]] && usage

    # Check all provided files
    for file in "$@"; do
        check_file "$file" || true
    done

    # Report results
    if [[ $files_checked -eq 0 ]]; then
        echo "ℹ️  No shell scripts to check"
        exit 0
    fi

    if [[ $errors -gt 0 ]]; then
        echo ""
        echo "❌ Found $errors issue(s) in shell scripts"
        provide_suggestions
        exit 1
    else
        echo "✓ No polling anti-patterns detected in $files_checked file(s)"
        exit 0
    fi
}

main "$@"
