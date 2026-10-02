#!/bin/bash

# ============================================================================
# issue-dashboard status for i3blocks: issues to do, agents working, work
# ready to merge, and merged issues awaiting their opener's close.
#
# Opened the same way as book_guard.sh: a click runs issue-dashboard-desktop,
# which reuses the dashboard server if it is answering (starting it detached
# if not) and opens an app window onto it.
#
# Reads the status.json the dashboard server rewrites on every refresh (every
# poll period, ~45 s, with or without a browser open) -- no network, no gh.
# Zero forks on the hot path: one builtin read, regex matches and a printf
# clock. Never blank: a missing or stale file means the server is not
# running, and is shown as a grey "dashboard" rather than old numbers.
# ============================================================================

set -euo pipefail

readonly STATUS="${ISSUE_DASHBOARD_STATUS:-$HOME/data/issue-dashboard/status.json}"
readonly LAUNCHER="${ISSUE_DASHBOARD_DESKTOP:-$HOME/.local/bin/issue-dashboard-desktop}"
# Four missed refreshes: past this the server is gone, not just slow.
readonly STALE_SECONDS=180

# Dracula-ish palette, matching the other blocks in this bar.
readonly RED='#FF5555'
readonly GREEN='#50FA7B'
readonly WHITE='#FFFFFF'
readonly GREY='#6272A4'

emit() {
	# full_text, short_text, color — the three lines i3blocks reads.
	printf '%s\n%s\n%s\n' "$1" "$2" "$3"
}

# The only fork, and only on a click: open (or reuse) the dashboard window.
if [[ ${BLOCK_BUTTON:-0} -ne 0 ]]; then
	setsid -f "$LAUNCHER" >/dev/null 2>&1 || true
fi

# status.json is one line of flat JSON written atomically by the server.
line=''
if [[ -r $STATUS ]]; then
	IFS= read -r line <"$STATUS" || true
fi

# field <name>: the integer value of a top-level key, or "" if absent.
field() {
	if [[ $line =~ \"$1\":\ *([0-9]+) ]]; then
		printf -v "$1" '%s' "${BASH_REMATCH[1]}"
	else
		printf -v "$1" '%s' ''
	fi
}

field todo
field working
field ready
field failed
field awaiting
field updated_epoch

if [[ -z $todo || -z $working || -z $ready || -z $failed || -z $updated_epoch ]]; then
	emit '📋 dashboard' '📋' "$GREY"
	exit 0
fi

printf -v now '%(%s)T' -1
if ((now - updated_epoch > STALE_SECONDS)); then
	emit '📋 dashboard' '📋' "$GREY"
	exit 0
fi

text="📋 ${todo} · ⚙ ${working} · ✓ ${ready}"
# Merged, waiting for the opener to close: shown only when there is some, and
# never a colour, since it waits on someone else. Optional because a server
# older than the awaiting column does not write it.
if ((${awaiting:-0} > 0)); then
	text="$text · ⏳ ${awaiting}"
fi
short="📋 ${todo}"
color=$WHITE
if ((failed > 0)); then
	text="$text · ✗ ${failed}"
	color=$RED
elif ((ready > 0)); then
	color=$GREEN
fi

emit "$text" "$short" "$color"
