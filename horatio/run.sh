#!/bin/bash
# ============================================================================
# Horatio — build, test, and run script for Arch Linux
#
# Prerequisites:
#   - Dart SDK (dart)   — pacman -S dart
#   - Flutter SDK        — flutter-bin (AUR) or manual install
#   - pip               — for openai-whisper (Linux speech-to-text)
#
# Usage:
#   ./run.sh              # Full pipeline: analyze + test + run
#   ./run.sh test         # Run core tests only
#   ./run.sh analyze      # Run analysis only
#   ./run.sh run          # Build and launch the desktop app
#   ./run.sh web          # Run as Flutter web app (for inspection/testing)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly CORE_DIR="$SCRIPT_DIR/horatio_core"
readonly APP_DIR="$SCRIPT_DIR/horatio_app"

# -- Helpers -----------------------------------------------------------------

check_command() {
    local cmd="$1"
    local pkg="$2"
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: '$cmd' not found. Install with: $pkg"
        exit 1
    fi
}

heading() {
    echo ""
    echo "══════════════════════════════════════════════════════════════"
    echo "  $1"
    echo "══════════════════════════════════════════════════════════════"
}

# Parses an lcov.info file and fails if coverage is below the threshold.
#   $1: path to lcov.info
#   $2: package name (for error messages)
#   $3: minimum coverage percentage (integer, e.g. 100)
check_coverage() {
    local lcov_file="$1"
    local pkg_name="$2"
    local threshold="$3"

    if [[ ! -f "$lcov_file" ]]; then
        echo "ERROR: Coverage file not found: $lcov_file"
        exit 1
    fi

    local coverage
    coverage=$(awk -F'[,:]' '
        /^DA:/ { total++; if ($3 == 0) uncov++ }
        END {
            if (total == 0) { print 0; exit }
            printf "%.1f", ((total - uncov) / total) * 100
        }
    ' "$lcov_file")

    echo "  $pkg_name coverage: ${coverage}% (threshold: ${threshold}%)"

    # Compare as integers (awk handles the float comparison).
    if awk "BEGIN { exit !(${coverage} < ${threshold}) }"; then
        echo "ERROR: $pkg_name coverage ${coverage}% is below ${threshold}%."
        exit 1
    fi
}

# -- Dependency checks -------------------------------------------------------

check_deps() {
    if ! command -v dart &>/dev/null; then
        # dart may come from flutter-bin; install standalone only if flutter is also missing.
        if ! command -v flutter &>/dev/null; then
            echo "ERROR: 'dart' not found. Install with: pacman -S dart"
            exit 1
        fi
    fi
}

ensure_whisper() {
    if command -v whisper &>/dev/null; then
        return
    fi

    heading "Installing OpenAI Whisper (Linux speech-to-text)"
    check_command pipx "pacman -S python-pipx"
    pipx install openai-whisper
    check_command whisper "pipx install openai-whisper"
}

ensure_flutter() {
    if command -v flutter &>/dev/null; then
        return
    fi

    heading "Installing Flutter SDK"
    if ! command -v pacman &>/dev/null; then
        echo "ERROR: 'flutter' not found and no pacman available."
        echo "Install from: https://flutter.dev/docs/get-started/install"
        exit 1
    fi

    # flutter-bin bundles Dart and conflicts with the standalone dart package.
    if pacman -Qi dart &>/dev/null; then
        echo "Removing standalone 'dart' package (flutter-bin includes Dart)..."
        sudo pacman -Rdd --noconfirm dart
    fi

    echo "Flutter not found — installing flutter-bin via AUR..."
    if command -v yay &>/dev/null; then
        yay -S --needed --noconfirm flutter-bin
    elif command -v paru &>/dev/null; then
        paru -S --needed --noconfirm flutter-bin
    else
        echo "ERROR: No AUR helper (yay/paru) found."
        echo "Install manually: yay -S flutter-bin  (or from flutter.dev)"
        exit 1
    fi

    # Verify it worked.
    check_command flutter "yay -S flutter-bin"
}

# -- Core package tasks ------------------------------------------------------

core_get() {
    heading "Upgrading core dependencies"
    cd "$CORE_DIR"
    dart pub upgrade --major-versions
}

core_analyze() {
    heading "Analyzing horatio_core"
    cd "$CORE_DIR"
    dart analyze --fatal-infos
}

core_test() {
    heading "Testing horatio_core (with coverage)"
    cd "$CORE_DIR"
    dart run coverage:test_with_coverage
    check_coverage "$CORE_DIR/coverage/lcov.info" "horatio_core" 100
}

core_format() {
    heading "Formatting horatio_core"
    cd "$CORE_DIR"
    dart format --set-exit-if-changed .
}

# -- App tasks ---------------------------------------------------------------

app_get() {
    heading "Upgrading app dependencies"
    cd "$APP_DIR"
    flutter pub upgrade --major-versions
}

app_analyze() {
    heading "Analyzing horatio_app"
    cd "$APP_DIR"
    flutter analyze --fatal-infos
}

app_test() {
    heading "Testing horatio_app (with coverage)"
    cd "$APP_DIR"
    flutter test --coverage
    check_coverage "$APP_DIR/coverage/lcov.info" "horatio_app" 100
}

app_build() {
    heading "Building horatio_app (Linux desktop)"
    cd "$APP_DIR"
    flutter build linux --release
}

app_run() {
    heading "Running horatio_app (Linux desktop)"
    cd "$APP_DIR"
    flutter run -d linux
}

app_web() {
    heading "Running horatio_app (Flutter web — for inspection)"
    cd "$APP_DIR"
    flutter run -d chrome --web-port=8080
}

# -- Pipelines ---------------------------------------------------------------

do_dead_code() {
    heading "Dead code detection & auto-removal"
    bash "$SCRIPT_DIR/dead_code.sh"
}

do_analyze() {
    check_deps
    core_get
    core_format
    core_analyze
    ensure_flutter
    app_get
    do_dead_code
}

do_test() {
    check_deps
    core_get
    core_test
    ensure_flutter
    app_get
    app_test
}

do_full() {
    do_analyze
    do_test
    do_run
    echo ""
    echo "All checks passed."
}

do_run() {
    check_deps
    ensure_flutter
    ensure_whisper
    core_get
    app_get
    app_analyze
    app_build
    app_run
}

do_web() {
    check_deps
    ensure_flutter
    ensure_whisper
    core_get
    app_get
    app_analyze
    app_web
}

# -- Main --------------------------------------------------------------------

main() {
    local cmd="${1:-full}"

    case "$cmd" in
        analyze)    do_analyze ;;
        test)       do_test ;;
        dead-code)  do_dead_code ;;
        full)       do_full ;;
        run)        do_run ;;
        web)        do_web ;;
        *)
            echo "Usage: $0 {analyze|test|dead-code|full|run|web}"
            exit 1
            ;;
    esac
}

main "$@"
