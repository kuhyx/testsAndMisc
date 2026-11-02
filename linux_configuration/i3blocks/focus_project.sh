#!/bin/bash

# ============================================================================
# Active focus project for i3blocks: `🎯 HackerRank prep 45/120` (minutes done
# today / daily target). Green once the daily target is reached, yellow while
# short of it, hidden when no project is active.
#
# Renders the `focus` field of daily-limits' cache ($XDG_RUNTIME_DIR/
# daily-limits.json, rewritten every 60 s by its user timer) and owns no
# focus logic: focus_project.status() decides. The cache is re-parsed with jq
# only when its mtime changes, so a steady-state tick forks nothing.
#
# Refresh is event-driven: the block has `signal=11` in the i3blocks config and
# daily-limits sends `pkill -RTMIN+11 -x i3blocks` the moment the focus status
# changes (the 30 s interval is only the fallback).
#
# A missing, garbage or >180 s old cache hides the block: the neighbouring
# gaming_budget block already says "⏱?" for the same cache, and old minutes
# must never be shown. Left-click opens `daily-limits --gui`.
# ============================================================================

set -euo pipefail

readonly LIMITS_CACHE="${DAILY_LIMITS_CACHE:-${XDG_RUNTIME_DIR:-/run/user/$UID}/daily-limits.json}"
readonly RENDER_CACHE="${DAILY_LIMITS_RENDER_CACHE:-${XDG_RUNTIME_DIR:-/run/user/$UID}/i3blocks-focus-project.render}"
readonly STALE_AFTER_SECONDS=180

# Dracula-ish palette, matching gaming_budget.sh.
readonly YELLOW='#F1FA8C'
readonly GREEN='#50FA7B'

emit() {
	# full_text, short_text, color: the three lines i3blocks reads.
	printf '%s\n%s\n%s\n' "$1" "$2" "$3"
}

# i3blocks' PATH has no ~/.local/bin, where daily-limits' install.sh puts it.
readonly DAILY_LIMITS_BIN=${DAILY_LIMITS_BIN:-$HOME/.local/bin/daily-limits}
if [[ ${BLOCK_BUTTON:-0} -eq 1 && -x $DAILY_LIMITS_BIN ]]; then
	setsid -f "$DAILY_LIMITS_BIN" --gui >/dev/null 2>&1
fi

hide() {
	emit '' '' "$YELLOW"
	exit 0
}

# One jq pass renders four lines: generated_at, full text, short text, color.
# The name is untrusted display text: control characters become spaces so it
# can never add lines to the block's output.
render_focus() {
	local rendered
	rendered=$(jq -r --arg green "$GREEN" --arg yellow "$YELLOW" '
		(.generated_at | if type == "number" then floor else "none" end),
		(.focus | if type == "object" and (.project | type) == "string" then
			(.minutes // 0 | floor) as $m
			| (.daily_minutes // 0 | floor) as $d
			| ((.name // .project) | tostring | gsub("[\u0001-\u001f\u007f]"; " ")) as $name
			| "🎯 \($name) \($m)/\($d)", "🎯 \($m)/\($d)",
			  (if $d > 0 and $m >= $d then $green else $yellow end)
		  else "", "", $yellow end)' "$LIMITS_CACHE" 2>/dev/null) || return 1
	printf '%s\n' "$rendered" >"$RENDER_CACHE"
}

[[ -r $LIMITS_CACHE ]] || hide
if [[ $LIMITS_CACHE -nt $RENDER_CACHE ]]; then
	command -v jq >/dev/null 2>&1 || hide
	render_focus || hide
fi

{
	read -r generated_at
	read -r full_text
	read -r short_text
	read -r color
} <"$RENDER_CACHE" || hide

if [[ -n ${NOW_EPOCH:-} ]]; then
	now=$NOW_EPOCH
else
	printf -v now '%(%s)T' -1
fi
[[ $generated_at =~ ^-?[0-9]+$ ]] || hide
age=$((now - generated_at))
if ((age > STALE_AFTER_SECONDS || age < -STALE_AFTER_SECONDS)); then
	hide
fi

emit "$full_text" "$short_text" "$color"
