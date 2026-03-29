#!/bin/bash
# ============================================================================
# Dead code detection and auto-removal for Horatio Dart/Flutter packages.
#
# Phase 1: dart fix --apply  (auto-remove what's fixable)
# Phase 2: dart/flutter analyze  (detect remaining dead code diagnostics)
#
# Exit code 0 = clean, 1 = dead code remains after auto-fix.
#
# Usage:
#   ./dead_code.sh              # Auto-fix + report (both packages)
#   ./dead_code.sh --dry-run    # Report only, no modifications
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly CORE_DIR="$SCRIPT_DIR/horatio_core"
readonly APP_DIR="$SCRIPT_DIR/horatio_app"

# Diagnostic codes that indicate dead/unreachable code.
readonly DEAD_CODE_PATTERN='unused_element|unused_field|unused_local_variable|unreachable_from_main|dead_code|unused_import'

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

heading() {
    echo ""
    echo "── $1 ──"
}

# Phase 1: auto-fix.
auto_fix() {
    local dir="$1"
    local name="$2"

    if $DRY_RUN; then
        heading "$name: dart fix --dry-run"
        cd "$dir"
        dart fix --dry-run || true
        return
    fi

    heading "$name: dart fix --apply"
    cd "$dir"
    dart fix --apply || true
}

# Phase 2: analyze and grep for dead-code diagnostics.
# Returns the number of dead-code findings (0 = clean).
check_dead_code() {
    local dir="$1"
    local name="$2"
    local analyze_cmd="$3"

    heading "$name: checking for dead code"
    cd "$dir"

    local output
    output=$($analyze_cmd 2>&1) || true

    local findings
    findings=$(echo "$output" | grep -cE "$DEAD_CODE_PATTERN" || true)

    if [[ "$findings" -gt 0 ]]; then
        echo "$output" | grep -E "$DEAD_CODE_PATTERN"
        echo ""
        echo "  $name: $findings dead-code diagnostic(s) remaining."
        return 1
    fi

    echo "  $name: no dead code found."
    return 0
}

main() {
    local failed=0

    auto_fix "$CORE_DIR" "horatio_core"
    auto_fix "$APP_DIR" "horatio_app"

    check_dead_code "$CORE_DIR" "horatio_core" "dart analyze" || failed=1
    check_dead_code "$APP_DIR" "horatio_app" "flutter analyze" || failed=1

    echo ""
    if [[ "$failed" -ne 0 ]]; then
        echo "DEAD CODE DETECTED — review the diagnostics above and remove the unused declarations."
        exit 1
    fi

    echo "All clean — no dead code found."
}

main
