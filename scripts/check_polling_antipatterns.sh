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
    local file_errors=0
    local line_num=0
    local in_polling_function=0
    # shellcheck disable=SC2034
    local function_name=""

    # Skip non-shell files
    if ! grep -q "#!/bin/bash\|#!/bin/sh\|#!/usr/bin/env bash" "$file" 2>/dev/null; then
        return 0
    fi

    files_checked=$((files_checked + 1))

    # Line-by-line check
    while IFS= read -r line; do
        line_num=$((line_num + 1))

        # Track if we're in a polling-related function
        if [[ $line =~ ^[[:space:]]*(.*_loop|.*_daemon|poll.*)\(\) ]]; then
            in_polling_function=1
            # shellcheck disable=SC2034
            function_name="${BASH_REMATCH[1]}"
        elif [[ $line =~ ^[[:space:]]*\} ]]; then
            in_polling_function=0
        fi

        # Only check within potential polling contexts
        if [[ $in_polling_function -eq 1 ]]; then
            # Check for while true + sleep (classic polling anti-pattern)
            if [[ $line =~ while[[:space:]]+(true|:) ]] && [[ $line =~ sleep ]]; then
                echo "  Line $line_num: ❌ while true/: + sleep detected (use event-driven I/O)"
                file_errors=$((file_errors + 1))
            fi

            # Check for $(date ...) or `date ...` in loops
            if [[ $line =~ \$\(date[[:space:]] ]] || [[ $line =~ \`date[[:space:]] ]]; then
                echo "  Line $line_num: ❌ date fork in polling function (optimize with single invocation)"
                file_errors=$((file_errors + 1))
            fi

            # Check for pgrep in loops
            if [[ $line =~ \bpgrep\b ]]; then
                echo "  Line $line_num: ❌ pgrep in polling context (consider alternatives or cache PID)"
                file_errors=$((file_errors + 1))
            fi

            # Check for xdotool in loops
            if [[ $line =~ \bxdotool\b ]]; then
                echo "  Line $line_num: ❌ xdotool in polling context (high fork overhead)"
                file_errors=$((file_errors + 1))
            fi

            # Check for aggressive polling (sleep < 1s)
            if [[ $line =~ sleep[[:space:]]+0\.[0-9] ]]; then
                echo "  Line $line_num: ⚠️  Aggressive polling (sleep < 1s)"
                file_errors=$((file_errors + 1))
            fi
        fi

        # Check for excessive pipe chains (each | is a fork)
        # Skip lines that are variable assignments or comments
        if [[ ! $line =~ = ]] && [[ ! $line =~ ^[[:space:]]*# ]]; then
            local pipe_count
            pipe_count=$(echo "$line" | tr -cd '|' | wc -c)
            if [[ $pipe_count -gt 3 ]]; then
                echo "  Line $line_num: ⚠️  Excessive pipes ($pipe_count pipes = many forks)"
                file_errors=$((file_errors + 1))
            fi
        fi

    done < "$file"

    if [[ $file_errors -gt 0 ]]; then
        errors=$((errors + file_errors))
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
