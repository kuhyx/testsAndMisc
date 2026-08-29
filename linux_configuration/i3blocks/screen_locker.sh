#!/bin/bash

# ============================================================================
# Screen-locker status for i3blocks.
#
# Replaces the GTK tray icon that sat commented out in ~/.config/i3/config from
# 2026-08-21, during which the locker miscounted the week and nothing on the
# machine said so. The point of this block is that a broken or disarmed locker
# is visible without being asked: it is never blank and never silently green.
#
# Reads the local status API (screen-locker-web.service). Click opens the UI.
# ============================================================================

set -euo pipefail

readonly API='http://127.0.0.1:8770/api/status'
readonly HEALTH='http://127.0.0.1:8770/api/health'
readonly UI='http://127.0.0.1:8770/'
readonly CACHE="${XDG_RUNTIME_DIR:-/tmp}/i3blocks-screen-locker.cache"

# Dracula-ish palette, matching the other blocks in this bar.
readonly RED='#FF5555'
readonly YELLOW='#F1FA8C'
readonly GREEN='#50FA7B'
readonly ORANGE='#FFB86C'

emit() {
	# full_text, short_text, color — the three lines i3blocks reads.
	printf '%s\n%s\n%s\n' "$1" "$2" "$3"
}

# A click opens the web UI rather than doing anything destructive; there is no
# action here that could clear a lock.
if [[ ${BLOCK_BUTTON:-0} -ne 0 ]]; then
	xdg-open "$UI" >/dev/null 2>&1 &
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
	emit '💪 no curl/jq' '💪 ?' "$ORANGE"
	exit 0
fi

status_json=$(curl -fsS --max-time 2 "$API" 2>/dev/null || true)
if [[ -z $status_json ]]; then
	# The server being down is itself news: it is what the gaming budget reads,
	# and it failing closed costs two hours. Say so instead of showing nothing.
	if [[ -r $CACHE ]]; then
		emit "$(cat "$CACHE") (stale)" '💪 ?' "$ORANGE"
	else
		emit '💪 status server down' '💪 ?' "$RED"
	fi
	exit 0
fi

count=$(jq -r '.snapshot.week.counted_count' <<<"$status_json")
minimum=$(jq -r '.snapshot.week.minimum' <<<"$status_json")
state=$(jq -r '.compliance_state' <<<"$status_json")
workout_today=$(jq -r '.gaming.workout_today' <<<"$status_json")

if [[ $workout_today == 'true' ]]; then
	hours='8h'
else
	hours='6h'
fi

health_json=$(curl -fsS --max-time 2 "$HEALTH" 2>/dev/null || true)
armed=$(jq -r '.armed' <<<"${health_json:-{\}}" 2>/dev/null || echo 'unknown')

text="💪 ${count}/${minimum} · ${hours}"
case $state in
lock) color=$RED ;;
warn) color=$YELLOW ;;
*) color=$GREEN ;;
esac

# Arming beats compliance: a locker that cannot fire is the worse problem, and
# it is the one that hides. Never render it as a green tick.
if [[ $armed != 'true' ]]; then
	text="$text ⚠ DISARMED"
	color=$RED
fi

printf '%s' "$text" >"$CACHE"
emit "$text" "💪 ${count}/${minimum}" "$color"
