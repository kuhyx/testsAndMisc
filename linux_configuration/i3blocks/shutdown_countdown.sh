#!/bin/bash
# Shutdown countdown status script for i3blocks.
# Shows the exact absolute time of the next enforced shutdown, or the
# overridden time if a shutdown-override-manager.sh window rescues it.
#
# The applied time and the still-unearned earners come from daily-limits'
# cache ($XDG_RUNTIME_DIR/daily-limits.json, rewritten every 60 s); this
# script owns no earner logic. The cache is re-parsed with jq only when its
# mtime changes, the rendered result is kept in a small file, so a steady-state
# tick forks nothing. A missing or >180 s old cache shows a "⏱?" marker (and
# the config-derived time), never old cache numbers. Left-click opens
# `daily-limits --gui`.

set -euo pipefail

SHUTDOWN_CONFIG=${SHUTDOWN_CONFIG:-/etc/shutdown-schedule.conf}
SKIP_DATES_FILE=${SKIP_DATES_FILE:-/etc/shutdown-skip-dates}
OVERRIDES_FILE=${OVERRIDES_FILE:-/etc/shutdown-schedule-overrides.conf}
LIMITS_CACHE=${DAILY_LIMITS_CACHE:-${XDG_RUNTIME_DIR:-/tmp}/daily-limits.json}
RENDER_CACHE=${DAILY_LIMITS_RENDER_CACHE:-${XDG_RUNTIME_DIR:-/tmp}/i3blocks-shutdown.render}
readonly STALE_AFTER_SECONDS=180

# Left-click: open the daily-limits popup (a fork only on click).
if [[ ${BLOCK_BUTTON:-0} -eq 1 ]] && command -v daily-limits >/dev/null 2>&1; then
	daily-limits --gui >/dev/null 2>&1 &
fi

# Function to show error state in i3blocks and exit
show_error() {
	local message="$1"
	echo "⏻ $message"
	echo "⏻"
	echo "#FF79C6" # Pink/magenta for config errors
	exit 0
}

if [[ ! -f $SHUTDOWN_CONFIG ]]; then
	show_error "NO CONFIG"
fi

# Times are minutes after midnight: the *_MINUTES keys when present, else the
# legacy whole-hour *_HOUR keys (a config written before the migration).
MON_WED_HOUR=''
THU_SUN_HOUR=''
morning_end_hour='5'
mon_wed_minutes=''
thu_sun_minutes=''
morning_end_minutes=''
while IFS='=' read -r key value; do
	value=${value%%[[:space:]]*}
	case $key in
	MON_WED_HOUR) MON_WED_HOUR=$value ;;
	THU_SUN_HOUR) THU_SUN_HOUR=$value ;;
	MORNING_END_HOUR) morning_end_hour=$value ;;
	MON_WED_MINUTES) mon_wed_minutes=$value ;;
	THU_SUN_MINUTES) thu_sun_minutes=$value ;;
	MORNING_END_MINUTES) morning_end_minutes=$value ;;
	esac
done <"$SHUTDOWN_CONFIG"

if [[ -z $mon_wed_minutes$MON_WED_HOUR ]] || [[ -z $thu_sun_minutes$THU_SUN_HOUR ]]; then
	show_error "MISSING VARS"
fi

for hour in "$MON_WED_HOUR" "$THU_SUN_HOUR" "$morning_end_hour"; do
	if [[ -n $hour ]] && ! [[ $hour =~ ^[0-9]+$ ]]; then
		show_error "INVALID HOURS"
	fi
done
[[ -n $mon_wed_minutes ]] || mon_wed_minutes=$((10#$MON_WED_HOUR * 60))
[[ -n $thu_sun_minutes ]] || thu_sun_minutes=$((10#$THU_SUN_HOUR * 60))
[[ -n $morning_end_minutes ]] || morning_end_minutes=$((10#$morning_end_hour * 60))
for minutes in "$mon_wed_minutes" "$thu_sun_minutes" "$morning_end_minutes"; do
	if ! [[ $minutes =~ ^[0-9]+$ ]] || ((10#$minutes > 1440)); then
		show_error "INVALID TIME"
	fi
done

get_now_epoch() {
	if [[ -n ${NOW_EPOCH:-} ]]; then
		printf '%s\n' "$NOW_EPOCH"
	else
		printf '%(%s)T\n' -1
	fi
}

now_epoch=$(get_now_epoch)
printf -v today_date '%(%Y-%m-%d)T' "$now_epoch"
# Fork-free whole-line match against the skip-dates file (bash builtin read,
# no `grep` process spawned every tick). Equivalent to `grep -qxF`.
if [[ -r $SKIP_DATES_FILE ]]; then
	while IFS= read -r skip_date || [[ -n $skip_date ]]; do
		if [[ $skip_date == "$today_date" ]]; then
			exit 0
		fi
	done <"$SKIP_DATES_FILE"
fi

printf -v current_hour '%(%H)T' "$now_epoch"
printf -v current_minute '%(%M)T' "$now_epoch"
printf -v current_second '%(%S)T' "$now_epoch"
printf -v day_of_week '%(%u)T' "$now_epoch"

current_time_minutes=$((10#$current_hour * 60 + 10#$current_minute))
morning_end_minutes=$((10#$morning_end_minutes))
midnight_epoch=$((now_epoch - (10#$current_hour * 3600 + 10#$current_minute * 60 + 10#$current_second)))

if [[ $day_of_week -ge 1 ]] && [[ $day_of_week -le 3 ]]; then
	shutdown_time_minutes=$((10#$mon_wed_minutes))
else
	shutdown_time_minutes=$((10#$thu_sun_minutes))
fi

shutdown_epoch_today=$((midnight_epoch + shutdown_time_minutes * 60))

# Prints "start_epoch|end_epoch|reason" for the first registered override
# (shutdown-override-manager.sh) whose window covers the given epoch, empty
# otherwise. Builtin `read` only - no forks in this hot path.
find_override_covering() {
	local target_epoch=$1
	[[ -f $OVERRIDES_FILE ]] || return 1
	local start_epoch end_epoch _created reason
	while IFS='|' read -r start_epoch end_epoch _created reason; do
		[[ -n $start_epoch ]] || continue
		if [[ $target_epoch -ge $start_epoch ]] && [[ $target_epoch -le $end_epoch ]]; then
			printf '%s|%s|%s\n' "$start_epoch" "$end_epoch" "$reason"
			return 0
		fi
	done <"$OVERRIDES_FILE"
	return 1
}

format_hhmm() {
	printf '%(%H:%M)T' "$1"
}

# Case 1: an override is active right now - always takes priority, whether
# or not we are inside the normal blocked window.
if override_match=$(find_override_covering "$now_epoch"); then
	IFS='|' read -r _ override_end _ <<<"$override_match"
	echo "▶ $(format_hhmm "$override_end") (override)"
	echo "▶ $(format_hhmm "$override_end")"
	echo "#50FA7B"
	exit 0
fi

# Case 2: currently inside the normal blocked window with no rescuing
# override registered - shutdown is due now.
if [[ $current_time_minutes -ge $shutdown_time_minutes ]] || [[ $current_time_minutes -le $morning_end_minutes ]]; then
	echo "⏻ SHUTDOWN"
	echo "⏻"
	echo "#FF5555"
	exit 0
fi

# Case 3: normal usable time. Show the exact hour of the next shutdown,
# unless a registered override starts before it and extends past it - in
# which case show the rescued (overridden) time instead, proactively.
if override_match=$(find_override_covering "$shutdown_epoch_today"); then
	IFS='|' read -r _ override_end _ <<<"$override_match"
	echo "▶ $(format_hhmm "$override_end") (override)"
	echo "▶ $(format_hhmm "$override_end")"
	echo "#50FA7B"
	exit 0
fi

# One jq pass renders three lines: generated_at, the applied shutdown time
# (falling back to the resolved one) and the hint for earners still in `todo`,
# e.g. " +🧩1h +📖?1h →max 23:00" ("?" = status unknown, still counted). "→max"
# appears once the cumulative `shutdown_after` of the todo list reaches the ceiling.
# Re-run only when the cache file is newer than the render.
render_limits() {
	local rendered
	command -v jq >/dev/null 2>&1 || return 1
	rendered=$(jq -r '
		def bonus_hm: . as $m
			| if $m < 60 then "\($m)m"
			else "\($m / 60 | floor)h" + ($m % 60 | if . == 0 then "" else "\(.)" | if length < 2 then "0" + . else . end end) end;
		{workout: "💪", leetcode: "🧩", reading: "📖", anki: "🗂", automation: "⚙"} as $icon
		| (.earners | map({(.name): .}) | add // {}) as $by
		| (.shutdown.applied // .shutdown.resolved) as $time
		| (.shutdown.ceiling) as $ceiling
		| (if $time < $ceiling and (.todo | length) > 0
			then " " + (.todo | map("+\($icon[.name] // .label)\(if .status == "unknown" then "?" else "" end)\($by[.name].shutdown_minutes // 0 | bonus_hm)") | join(" "))
				+ (if (.todo | map(.shutdown_after) | max) >= $ceiling then " →max \($ceiling)" else "" end)
			else "" end) as $hint
		| .generated_at, $time, $hint' "$LIMITS_CACHE" 2>/dev/null) || return 1
	printf '%s\n' "$rendered" >"$RENDER_CACHE"
}

# Sets limits_state (fresh|stale|missing|bad), limits_time, limits_hint, limits_age.
limits_state=missing
limits_time=''
limits_hint=''
limits_age=0
load_limits() {
	local gen=''
	[[ -r $LIMITS_CACHE ]] || return 0
	limits_state=bad
	if [[ $LIMITS_CACHE -nt $RENDER_CACHE ]]; then
		render_limits || return 0
	fi
	{
		read -r gen
		read -r limits_time
		IFS= read -r limits_hint || true
	} <"$RENDER_CACHE" 2>/dev/null || return 0
	[[ $gen =~ ^[0-9]+$ && $limits_time =~ ^[0-9]{2}:[0-9]{2}$ ]] || return 0
	limits_age=$((now_epoch - gen))
	if ((limits_age > STALE_AFTER_SECONDS || limits_age < -STALE_AFTER_SECONDS)); then
		limits_state=stale
	else
		limits_state=fresh
	fi
}

load_limits

printf -v shutdown_label '%(%H:%M)T' "$shutdown_epoch_today"
hint=''
case $limits_state in
fresh)
	shutdown_label=$limits_time
	hint=$limits_hint
	shutdown_time_minutes=$((10#${limits_time%:*} * 60 + 10#${limits_time#*:}))
	;;
stale) hint=" ⏱? $((limits_age / 60))m" ;;
missing) hint=' ⏱?' ;;
bad) hint=' ⏱!' ;;
esac

minutes_until_shutdown=$((shutdown_time_minutes - current_time_minutes))

if [[ $minutes_until_shutdown -le 30 ]]; then
	color="#FF5555"
elif [[ $minutes_until_shutdown -le 60 ]]; then
	color="#FFB86C"
elif [[ $minutes_until_shutdown -le 120 ]]; then
	color="#F1FA8C"
else
	color="#6272A4"
fi

echo "⏻ ${shutdown_label}${hint}"
echo "⏻"
echo "$color"
