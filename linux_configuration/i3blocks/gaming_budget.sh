#!/bin/bash

# ============================================================================
# Gaming time budget for i3blocks: time left today, used/total, and which
# bonuses (workout, LeetCode, reading) are still there to be earned.
#
# Reads steam-backlog-enforcer's /api/budget, which already folds in the
# screen-locker, leetcode-guard and book-guard bonuses. Like screen_locker.sh
# it is never blank: a dead server shows the last value marked stale, or red.
# Click opens the enforcer's web UI.
# ============================================================================

set -euo pipefail

readonly API="${GAMING_BUDGET_API:-http://127.0.0.1:8000/api/budget}"
readonly UI='http://127.0.0.1:8000/'
# Only for the *size* of bonuses not yet earned; /api/budget reports earned
# ones as 0. The file holds secrets, so it goes to jq by path, never on argv.
readonly CONFIG="${GAMING_BUDGET_CONFIG:-$HOME/.config/steam_backlog_enforcer/config.json}"
readonly CACHE="${GAMING_BUDGET_CACHE:-${XDG_RUNTIME_DIR:-/tmp}/i3blocks-gaming-budget.cache}"

# Dracula-ish palette, matching screen_locker.sh.
readonly RED='#FF5555'
readonly YELLOW='#F1FA8C'
readonly GREEN='#50FA7B'
readonly ORANGE='#FFB86C'

emit() {
	# full_text, short_text, color — the three lines i3blocks reads.
	printf '%s\n%s\n%s\n' "$1" "$2" "$3"
}

if [[ ${BLOCK_BUTTON:-0} -ne 0 ]]; then
	xdg-open "$UI" >/dev/null 2>&1 &
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
	emit '🎮 no curl/jq' '🎮 ?' "$ORANGE"
	exit 0
fi

budget_json=$(curl -fsS --max-time 2 "$API" 2>/dev/null || true)
if [[ -z $budget_json ]]; then
	if [[ -r $CACHE ]]; then
		emit "$(<"$CACHE") (stale)" '🎮 ?' "$ORANGE"
	else
		emit '🎮 budget server down' '🎮 ?' "$RED"
	fi
	exit 0
fi

config_path=/dev/null
[[ -r $CONFIG ]] && config_path=$CONFIG

# One jq pass renders all three lines, so a tick costs curl + jq and no more.
# The first line is "cache" or "nocache": error states must not overwrite the
# last good value that the stale path shows.
# Thresholds mirror the enforcer's own warn_at (1h, 30m, 10m).
rendered=$(jq -r \
	--slurpfile cfg "$config_path" \
	--arg red "$RED" --arg orange "$ORANGE" --arg yellow "$YELLOW" --arg green "$GREEN" '
	def hm: (. / 60 | round) as $m
		| "\($m / 60 | floor)h\($m % 60 | tostring | if length < 2 then "0" + . else . end)";
	def bonus_hm: hm | sub("h00$"; "h");
	($cfg[0] // {}) as $c
	| if .state_status != "ok" then ["nocache", "🎮 state \(.state_status)", "🎮 !", $red]
	elif .ok != true then ["nocache", "🎮 budget error", "🎮 !", $red]
	else
		.today as $t
		| .rules.bonuses as $b
		| ([$t.seconds_remaining, 0] | max) as $left
		| "\($t.seconds_used | hm)/\($t.budget_seconds | hm)" as $ratio
		# Unearned bonuses: [earned, configured size (enforcer default), icon].
		| [ [$b.workout, ($c.workout_bonus_seconds // 7200), "💪"],
		    [$b.leetcode, ($c.leetcode_bonus_seconds // 3600), "🧩"],
		    [$b.reading, ($c.reading_bonus_seconds // 3600), "📖"] ]
		| map(select((.[0] // 0) == 0 and .[1] > 0) | "+\(.[2])\(.[1] | bonus_hm)")
		| (if length > 0 then " " + join(" ") else "" end) as $todo
		| if $t.blocked or $left <= 0 then
			["cache", "🎮 BLOCKED · \($ratio)\($todo)", "🎮 BLOCKED", $red]
		else
			["cache", "🎮 \($left | hm) left · \($ratio)\($todo)", "🎮 \($left | hm)",
			 (if $left <= 600 then $red
			  elif $left <= 1800 then $orange
			  elif $left <= 3600 then $yellow
			  else $green end)]
		end
	end
	| .[]' <<<"$budget_json" 2>/dev/null) || {
	emit '🎮 unreadable budget' '🎮 !' "$RED"
	exit 0
}

{
	read -r cache_flag
	read -r full_text
	read -r short_text
	read -r color
} <<<"$rendered"

[[ $cache_flag == 'cache' ]] && printf '%s' "$full_text" >"$CACHE"
emit "$full_text" "$short_text" "$color"
