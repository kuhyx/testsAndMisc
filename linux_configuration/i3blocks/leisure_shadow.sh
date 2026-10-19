#!/bin/bash

# ============================================================================
# Shadow-week leisure budget for i3blocks: what the leisure budget WOULD say
# (`🛋 SHADOW 3h12 left · 1h48 used`) while only games are enforced.
#
# Renders the `leisure_shadow` part of daily-limits' cache
# ($XDG_RUNTIME_DIR/daily-limits.json, rewritten every 60 s; contract C5) and
# owns no accounting. Same shape as gaming_budget.sh: jq re-parses only when
# the cache's mtime changes, the rendered block is kept in a small file, so a
# steady-state tick forks nothing. Missing numbers say "⏱? no data", never 0;
# a >180 s old cache says "stale". Yellow under 30 min, red at would-be 0.
# Never urgent: it always exits 0 (i3blocks flashes exit 33 as urgent).
# ============================================================================

set -euo pipefail

readonly LIMITS_CACHE="${DAILY_LIMITS_CACHE:-${XDG_RUNTIME_DIR:-/run/user/$UID}/daily-limits.json}"
readonly RENDER_CACHE="${LEISURE_SHADOW_RENDER_CACHE:-${XDG_RUNTIME_DIR:-/run/user/$UID}/i3blocks-leisure-shadow.render}"
readonly STALE_AFTER_SECONDS=180

# Dracula-ish palette, matching gaming_budget.sh.
readonly RED='#FF5555'
readonly YELLOW='#F1FA8C'
readonly ORANGE='#FFB86C'
readonly FOREGROUND='#F8F8F2'

emit() {
	# full_text, short_text, color — the three lines i3blocks reads.
	printf '%s\n%s\n%s\n' "$1" "$2" "$3"
}

# One jq pass renders four lines: generated_at, full text, short text, color.
render_shadow() {
	local rendered
	rendered=$(jq -r \
		--arg red "$RED" --arg yellow "$YELLOW" --arg orange "$ORANGE" \
		--arg fg "$FOREGROUND" '
		def hm: . as $m
			| "\($m / 60 | floor)h\($m % 60 | tostring | if length < 2 then "0" + . else . end)";
		(.leisure_shadow // {}) as $s
		| (.generated_at | if type == "number" then floor else "none" end),
		  (if $s.used_minutes == null or $s.budget_minutes == null then
			"🛋 SHADOW ⏱? no data", "🛋 ⏱?", $orange
		  elif $s.would_block or ($s.left_minutes // 0) <= 0 then
			"🛋 SHADOW WOULD BLOCK · \($s.used_minutes | hm) used", "🛋 WOULD BLOCK", $red
		  else
			"🛋 SHADOW \($s.left_minutes | hm) left · \($s.used_minutes | hm) used",
			"🛋 \($s.left_minutes | hm)",
			(if $s.left_minutes < 30 then $yellow else $fg end)
		  end)' "$LIMITS_CACHE" 2>/dev/null) || return 1
	printf '%s\n' "$rendered" >"$RENDER_CACHE"
}

if [[ ! -r $LIMITS_CACHE ]]; then
	emit '🛋 SHADOW ⏱? no data' '🛋 ⏱?' "$ORANGE"
	exit 0
fi

if [[ $LIMITS_CACHE -nt $RENDER_CACHE ]]; then
	if ! command -v jq >/dev/null 2>&1; then
		emit '🛋 SHADOW no jq' '🛋 ?' "$ORANGE"
		exit 0
	fi
	render_shadow || {
		emit '🛋 SHADOW unreadable cache' '🛋 !' "$RED"
		exit 0
	}
fi

{
	read -r generated_at
	read -r full_text
	read -r short_text
	read -r color
} <"$RENDER_CACHE" || {
	emit '🛋 SHADOW unreadable cache' '🛋 !' "$RED"
	exit 0
}

if [[ -n ${NOW_EPOCH:-} ]]; then
	now=$NOW_EPOCH
else
	printf -v now '%(%s)T' -1
fi
# A cache without a numeric generated_at cannot be dated: say so, never crash.
if [[ ! $generated_at =~ ^-?[0-9]+$ ]]; then
	emit '🛋 SHADOW ⏱? no data' '🛋 ⏱?' "$ORANGE"
	exit 0
fi
age=$((now - generated_at))
if ((age > STALE_AFTER_SECONDS || age < -STALE_AFTER_SECONDS)); then
	emit "🛋 SHADOW ⏱? stale $((age / 60))m" '🛋 ⏱?' "$ORANGE"
	exit 0
fi

emit "$full_text" "$short_text" "$color"
