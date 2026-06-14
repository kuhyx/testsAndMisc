#!/usr/bin/env bash

# ============================================================================
# volume_control.sh — adjust PulseAudio volume / mute via pactl
# ============================================================================
# Single entry point for media-key bindings in i3 and dwm. Shows a transient
# desktop notification (best-effort). Replaces the long-missing ~/volume_control.sh
# that both window-manager configs referenced.
#
# Usage: volume_control.sh {up|down|mute|micmute}
#   up      raise output volume by VOLUME_STEP% (default 5) and unmute
#   down    lower output volume by VOLUME_STEP% and unmute
#   mute    toggle output (sink) mute
#   micmute toggle input (source) mute
# ============================================================================

set -euo pipefail

readonly SINK="@DEFAULT_SINK@"
readonly SOURCE="@DEFAULT_SOURCE@"
readonly STEP="${VOLUME_STEP:-5}"

# Best-effort notification; never fail the binding if no daemon is running.
notify() {
    command -v notify-send >/dev/null 2>&1 || return 0
    # Collapse repeated volume popups into one via a synchronous hint.
    notify-send -t 1200 -h string:x-canonical-private-synchronous:volume \
        "$1" "$2" 2>/dev/null || true
}

# First percentage pactl reports for the default sink (e.g. "45%").
current_sink_volume() {
    pactl get-sink-volume "$SINK" 2>/dev/null | grep -oE '[0-9]+%' | head -1 || true
}

case "${1:-}" in
    up)
        pactl set-sink-mute "$SINK" 0
        pactl set-sink-volume "$SINK" "+${STEP}%"
        notify "Volume" "$(current_sink_volume)"
        ;;
    down)
        pactl set-sink-mute "$SINK" 0
        pactl set-sink-volume "$SINK" "-${STEP}%"
        notify "Volume" "$(current_sink_volume)"
        ;;
    mute)
        pactl set-sink-mute "$SINK" toggle
        if pactl get-sink-mute "$SINK" 2>/dev/null | grep -q yes; then
            notify "Volume" "Muted"
        else
            notify "Volume" "$(current_sink_volume)"
        fi
        ;;
    micmute)
        pactl set-source-mute "$SOURCE" toggle
        if pactl get-source-mute "$SOURCE" 2>/dev/null | grep -q yes; then
            notify "Microphone" "Muted"
        else
            notify "Microphone" "On"
        fi
        ;;
    *)
        echo "Usage: $(basename "$0") {up|down|mute|micmute}" >&2
        exit 1
        ;;
esac
