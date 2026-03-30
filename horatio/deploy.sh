#!/bin/bash
# ============================================================================
# Horatio — build & deploy to Android device (BL-9000)
#
# Builds a release APK and installs it on the connected Android device.
# Supports wireless ADB (IP) or USB (auto-detect).
#
# Usage:
#   ./deploy.sh                  # Build + install (auto-detect USB device)
#   ./deploy.sh <phone_ip>       # Build + install via wireless ADB
#   ./deploy.sh --install-only   # Skip build, install existing APK
#   ./deploy.sh <ip> --install-only
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly APP_DIR="$SCRIPT_DIR/horatio_app"
readonly APK_PATH="$APP_DIR/build/app/outputs/flutter-apk/app-release.apk"

PHONE_IP=""
INSTALL_ONLY=false

# -- Argument parsing --------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --install-only) INSTALL_ONLY=true; shift ;;
        -*)             echo "Unknown flag: $1"; exit 1 ;;
        *)              PHONE_IP="$1"; shift ;;
    esac
done

# -- Helpers -----------------------------------------------------------------

heading() {
    echo ""
    echo "══════════════════════════════════════════════════════════════"
    echo "  $1"
    echo "══════════════════════════════════════════════════════════════"
}

check_command() {
    local cmd="$1"
    local install_hint="$2"
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: '$cmd' not found. Install with: $install_hint"
        exit 1
    fi
}

# -- ADB connection ----------------------------------------------------------

get_device_flag() {
    if [[ -n "$PHONE_IP" ]]; then
        echo "-s ${PHONE_IP}:5555"
    else
        echo ""
    fi
}

connect_device() {
    check_command adb "pacman -S android-tools"

    if [[ -n "$PHONE_IP" ]]; then
        heading "Connecting to $PHONE_IP via wireless ADB"
        adb connect "${PHONE_IP}:5555"
        sleep 1
        if ! adb devices | grep -q "$PHONE_IP"; then
            echo "ERROR: Could not connect to ${PHONE_IP}:5555"
            echo "Make sure wireless ADB is enabled and the phone is reachable."
            exit 1
        fi
        echo "Connected."
    else
        heading "Detecting USB device"
        local device_count
        device_count=$(adb devices | grep -c 'device$' || true)
        if [[ "$device_count" -eq 0 ]]; then
            echo "ERROR: No Android device connected via USB."
            echo "Connect BL-9000 with USB, or pass its IP: $0 <phone_ip>"
            exit 1
        elif [[ "$device_count" -gt 1 ]]; then
            echo "ERROR: Multiple devices detected. Specify IP or disconnect extras."
            adb devices
            exit 1
        fi
        echo "Found device: $(adb devices | grep 'device$' | awk '{print $1}')"
    fi
}

# -- Build -------------------------------------------------------------------

build_apk() {
    heading "Building Horatio APK (release)"

    check_command flutter "Install Flutter: https://flutter.dev/docs/get-started/install"

    cd "$APP_DIR"
    flutter pub get
    flutter build apk --release

    if [[ ! -f "$APK_PATH" ]]; then
        echo "ERROR: APK not found at $APK_PATH"
        exit 1
    fi

    local size
    size=$(du -h "$APK_PATH" | awk '{print $1}')
    echo "APK built: $APK_PATH ($size)"
}

# -- Install -----------------------------------------------------------------

install_apk() {
    heading "Installing Horatio on device"

    if [[ ! -f "$APK_PATH" ]]; then
        echo "ERROR: No APK found at $APK_PATH"
        echo "Run without --install-only to build first."
        exit 1
    fi

    local device_flag
    device_flag=$(get_device_flag)

    # shellcheck disable=SC2086
    adb $device_flag install -r "$APK_PATH"
    echo ""
    echo "Horatio installed successfully."
}

# -- Main --------------------------------------------------------------------

main() {
    connect_device

    if ! $INSTALL_ONLY; then
        build_apk
    fi

    install_apk

    echo ""
    echo "Done. Launch Horatio on BL-9000."
}

main
