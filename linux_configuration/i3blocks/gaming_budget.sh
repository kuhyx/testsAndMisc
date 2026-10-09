#!/bin/bash

# ============================================================================
# Gaming time budget for i3blocks: time left today, used/total, and which
# bonuses (workout, LeetCode, reading, Anki, Automation, ...) are still there
# to be earned.
#
# Renders daily-limits' cache ($XDG_RUNTIME_DIR/daily-limits.json, rewritten
# every 60 s) and owns no earner logic. The cache is re-parsed with jq only
# when its mtime changes; the rendered block is kept in a small file, so a
# steady-state tick forks nothing. A missing or >180 s old cache shows "⏱?",
# never old numbers. Left-click opens `daily-limits --gui`.
# ============================================================================

set -euo pipefail

readonly LIMITS_CACHE="${DAILY_LIMITS_CACHE:-${XDG_RUNTIME_DIR:-/tmp}/daily-limits.json}"
readonly RENDER_CACHE="${DAILY_LIMITS_RENDER_CACHE:-${XDG_RUNTIME_DIR:-/tmp}/i3blocks-gaming-budget.render}"
readonly STALE_AFTER_SECONDS=180

# Dracula-ish palette, matching screen_locker.sh.
readonly RED='#FF5555'
readonly YELLOW='#F1FA8C'
readonly GREEN='#50FA7B'
readonly ORANGE='#FFB86C'
readonly GREY='#6272A4'

emit() {
	# full_text, short_text, color — the three lines i3blocks reads.
	printf '%s\n%s\n%s\n' "$1" "$2" "$3"
}

# i3blocks' PATH has no ~/.local/bin, where daily-limits' install.sh puts it,
# so a bare `daily-limits` made every click a silent no-op.
readonly DAILY_LIMITS_BIN=${DAILY_LIMITS_BIN:-$HOME/.local/bin/daily-limits}
if [[ ${BLOCK_BUTTON:-0} -eq 1 ]]; then
	if [[ -x $DAILY_LIMITS_BIN ]]; then
		setsid -f "$DAILY_LIMITS_BIN" --gui >/dev/null 2>&1
	else
		notify-send -u critical 'daily-limits' "not installed: $DAILY_LIMITS_BIN" || true
	fi
fi

# One jq pass renders four lines: generated_at, full text, short text, color.
# Thresholds mirror the enforcer's own warn_at (1h, 30m, 10m). Bonuses still
# not done are listed as " +💪2h +🧩?1h" ("?" = status unknown, still counted);
# a gaming day other than the date is shown as " (10-08)"; used_minutes == null means the enforcer
# could not report usage, so only the budget is shown.
render_limits() {
	local rendered
	rendered=$(jq -r \
		--arg red "$RED" --arg orange "$ORANGE" --arg yellow "$YELLOW" \
		--arg green "$GREEN" --arg grey "$GREY" '
		def hm: . as $m
			| "\($m / 60 | floor)h\($m % 60 | tostring | if length < 2 then "0" + . else . end)";
		def bonus_hm: if . < 60 then "\(.)m" else hm | sub("h00$"; "h") end;
		{workout: "💪", leetcode: "🧩", reading: "📖", anki: "🗂", automation: "⚙"} as $icon
		| .gaming as $g
		| ([.earners[] | select(.status != "done" and .gaming_minutes > 0)
			| "+\($icon[.name] // .label)\(if .status == "unknown" then "?" else "" end)\(.gaming_minutes | bonus_hm)"]
			| if length > 0 then " " + join(" ") else "" end) as $todo
		| (if (.gaming.day // .date) != .date then " (\((.gaming.day // .date)[5:]))" else "" end) as $day
		| .generated_at,
		  (if $g.used_minutes == null then
			"🎮 budget \($g.budget_minutes | hm)\($day)\($todo)", "🎮 \($g.budget_minutes | hm)", $grey
		  else
			([$g.budget_minutes - $g.used_minutes, 0] | max) as $left
			| "\($g.used_minutes | hm)/\($g.budget_minutes | hm)\($day)" as $ratio
			| if $left <= 0 then
				"🎮 BLOCKED · \($ratio)\($todo)", "🎮 BLOCKED", $red
			else
				"🎮 \($left | hm) left · \($ratio)\($todo)", "🎮 \($left | hm)",
				(if $left <= 10 then $red
				 elif $left <= 30 then $orange
				 elif $left <= 60 then $yellow
				 else $green end)
			end
		  end)' "$LIMITS_CACHE" 2>/dev/null) || return 1
	printf '%s\n' "$rendered" >"$RENDER_CACHE"
}

if [[ ! -r $LIMITS_CACHE ]]; then
	emit '🎮 ⏱? no data' '🎮 ⏱?' "$ORANGE"
	exit 0
fi

if [[ $LIMITS_CACHE -nt $RENDER_CACHE ]]; then
	if ! command -v jq >/dev/null 2>&1; then
		emit '🎮 no jq' '🎮 ?' "$ORANGE"
		exit 0
	fi
	render_limits || {
		emit '🎮 unreadable cache' '🎮 !' "$RED"
		exit 0
	}
fi

{
	read -r generated_at
	read -r full_text
	read -r short_text
	read -r color
} <"$RENDER_CACHE" || {
	emit '🎮 unreadable cache' '🎮 !' "$RED"
	exit 0
}

if [[ -n ${NOW_EPOCH:-} ]]; then
	now=$NOW_EPOCH
else
	printf -v now '%(%s)T' -1
fi
age=$((now - generated_at))
if ((age > STALE_AFTER_SECONDS || age < -STALE_AFTER_SECONDS)); then
	emit "🎮 ⏱? stale $((age / 60))m" '🎮 ⏱?' "$ORANGE"
	exit 0
fi

emit "$full_text" "$short_text" "$color"
