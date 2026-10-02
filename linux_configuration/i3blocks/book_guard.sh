#!/bin/bash

# ============================================================================
# book-guard status for i3blocks: this month's paper-book pace.
#
# Sibling of screen_locker.sh, and opened the same way: a click opens the
# book-guard desktop window (book-guard-desktop serves the web app on :8773
# and, if it is already running, just opens another window onto it).
#
# Reads the state.json book-guard publishes into the Reading folder on every
# inbox pass (every 15 min) and every gate run -- no server needed. Like the
# screen-locker block it is never blank and never silently green: a missing
# or stale snapshot, or a disarmed timer, is shown as such.
# ============================================================================

set -euo pipefail

readonly STATE="${BOOK_GUARD_STATE:-$HOME/data/cloud/Reading/state.json}"
readonly LAUNCHER="${BOOK_GUARD_DESKTOP:-$HOME/.local/bin/book-guard-desktop}"
# Three missed inbox passes: past this the numbers describe a different hour.
readonly STALE_SECONDS=2700

# Dracula-ish palette, matching the other blocks in this bar.
readonly RED='#FF5555'
readonly YELLOW='#F1FA8C'
readonly GREEN='#50FA7B'
readonly ORANGE='#FFB86C'

emit() {
	# full_text, short_text, color — the three lines i3blocks reads.
	printf '%s\n%s\n%s\n' "$1" "$2" "$3"
}

# A click only opens the window; nothing here can clear a lock.
if [[ ${BLOCK_BUTTON:-0} -ne 0 ]]; then
	setsid -f "$LAUNCHER" >/dev/null 2>&1 || true
fi

if ! command -v jq >/dev/null 2>&1; then
	emit '📖 no jq' '📖 ?' "$ORANGE"
	exit 0
fi

if [[ ! -r $STATE ]] || ! jq -e '.pace' "$STATE" >/dev/null 2>&1; then
	emit '📖 no status' '📖 ?' "$ORANGE"
	exit 0
fi

# One jq pass, tab-separated: locked, pages, target, behind, reason.
IFS=$'\t' read -r locked pages target behind reason < <(
	jq -r '[.locked, .pace.pages, .pace.target, .pace.behind, .reason] | @tsv' "$STATE"
)

text="📖 ${pages}/${target}"
short="📖 ${pages}"
if [[ $locked == 'true' ]]; then
	text="$text · LOCKED, ${behind}p behind"
	color=$RED
elif ((behind > 0)); then
	# Behind but unlocked: the bar has room for a tag, not the full reason.
	case $reason in
	*escape*) why='escaped' ;;
	*free\ day*) why='free day' ;;
	*) why='unlocked' ;;
	esac
	text="$text · ${behind}p behind (${why})"
	color=$YELLOW
else
	text="$text ✓"
	color=$GREEN
fi

printf -v now '%(%s)T' -1
age=$((now - $(stat -c %Y "$STATE")))
if ((age > STALE_SECONDS)); then
	text="$text (stale $((age / 60))m)"
	color=$ORANGE
fi

# Arming beats pace, as in the screen-locker block: a gate that cannot fire
# is the worse problem, and it is the one that hides.
if ! systemctl --user is-active --quiet book-guard.timer; then
	text="$text ⚠ DISARMED"
	color=$RED
fi

emit "$text" "$short" "$color"
