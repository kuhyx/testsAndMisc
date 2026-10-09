#!/bin/bash
# Behaviour tests for shutdown_countdown.sh's rendering of daily-limits' cache
# ($DAILY_LIMITS_CACHE): the applied time, the unearned-earner hint (todo and
# unknown), the ceiling note driven by `shutdown_after`, and the stale/missing/
# garbage markers.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
BLOCK="$REPO_DIR/i3blocks/shutdown_countdown.sh"
TMP_DIR=$(mktemp -d)

cleanup() {
	rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
	printf 'FAIL: %s\n' "$1" >&2
	exit 1
}

assert_eq() {
	if [[ "$1" != "$2" ]]; then
		fail "$3 (expected '$1', actual '$2')"
	fi
}

printf '{}' | jq -e . >/dev/null 2>&1 ||
	fail 'a working jq is required for the shutdown hint tests (pacman -S jq)'

CACHE="$TMP_DIR/daily-limits.json"
RENDER="$TMP_DIR/render"
SCHEDULE="$TMP_DIR/schedule.conf"
NO_OVERRIDES="$TMP_DIR/overrides.conf"
: >"$NO_OVERRIDES"
# 2026-05-01 is a Friday, so THU_SUN_MINUTES applies.
NOW=$(TZ=UTC date -d '2026-05-01 18:00:00' +%s)
# write_cache APPLIED GENERATED_AT TODO... where TODO is NAME:STATUS:MINUTES:AFTER.
# APPLIED may be "null" (then resolved = 20:00 is shown). Each todo entry is also
# an earner, carrying its shutdown_minutes.
write_cache() {
	local applied=$1 generated=$2
	shift 2
	[[ $applied == null ]] || applied="\"$applied\""
	local earners=() todos=() name status minutes after spec
	for spec in "$@"; do
		IFS=: read -r name status minutes after <<<"$spec"
		earners+=("{\"name\":\"$name\",\"label\":\"$name\",\"status\":\"$status\",\"shutdown_minutes\":$minutes,\"gaming_minutes\":$minutes}")
		todos+=("{\"name\":\"$name\",\"label\":\"$name\",\"status\":\"$status\",\"shutdown_after\":\"$after\"}")
	done
	local IFS=,
	printf '{"date":"2026-05-01","generated_at":%s,"shutdown":{"applied":%s,"resolved":"20:00","floor":"20:00","ceiling":"23:00"},"gaming":{"budget_minutes":180,"used_minutes":null,"ceiling_minutes":480,"day":"2026-05-01"},"earners":[%s],"todo":[%s]}\n' \
		"$generated" "$applied" "${earners[*]}" "${todos[*]}" >"$CACHE"
	rm -f "$RENDER" # force a re-render for the new content
}

# first_line SHUTDOWN_MINUTES -- the block's full_text at 18:00.
first_line() {
	printf 'THU_SUN_MINUTES=%s\nMON_WED_MINUTES=%s\nMORNING_END_MINUTES=300\n' \
		"$1" "$1" >"$SCHEDULE"
	TZ=UTC NOW_EPOCH="$NOW" DAILY_LIMITS_CACHE="$CACHE" DAILY_LIMITS_RENDER_CACHE="$RENDER" \
		SHUTDOWN_CONFIG="$SCHEDULE" OVERRIDES_FILE="$NO_OVERRIDES" \
		SKIP_DATES_FILE=/dev/null bash "$BLOCK" | sed -n 1p
}

printf 'Checking not-done earners are listed with icon and amount...\n'
write_cache 20:00 "$NOW" leetcode:todo:60:21:00 reading:todo:60:22:00 anki:todo:30:22:30 automation:todo:30:23:00
assert_eq '⏻ 20:00 +🧩1h +📖1h +🗂30m +⚙30m →max 23:00' "$(first_line 1200)" \
	'cumulative shutdown_after reaching 23:00 gives the ceiling note'
write_cache 20:00 "$NOW" leetcode:todo:60:21:00 reading:todo:60:22:00
assert_eq '⏻ 20:00 +🧩1h +📖1h' "$(first_line 1200)" 'below the ceiling: no note'

printf 'Checking unknown earners are shown with ? and counted...\n'
write_cache 20:00 "$NOW" leetcode:unknown:60:21:00 reading:todo:60:22:00 anki:unknown:30:23:00
assert_eq '⏻ 20:00 +🧩?1h +📖1h +🗂?30m →max 23:00' "$(first_line 1200)" \
	'unknown marked, and its shutdown_after still drives →max'

printf 'Checking the applied time wins, resolved is the fallback...\n'
write_cache 21:30 "$NOW"
assert_eq '⏻ 21:30' "$(first_line 1200)" 'applied time shown'
write_cache null "$NOW"
assert_eq '⏻ 20:00' "$(first_line 1200)" 'applied null falls back to resolved'

printf 'Checking nothing is listed at the ceiling or with all done...\n'
write_cache 23:00 "$NOW" leetcode:todo:60:23:00
assert_eq '⏻ 23:00' "$(first_line 1380)" 'no headroom, no hint'
write_cache 20:00 "$NOW"
assert_eq '⏻ 20:00' "$(first_line 1200)" 'everything done'

printf 'Checking odd amounts and unmapped earners...\n'
write_cache 20:00 "$NOW" leetcode:todo:90:21:30 newgate:todo:15:21:45
assert_eq '⏻ 20:00 +🧩1h30 +newgate15m' "$(first_line 1200)" \
	'1h30 padded like gaming_budget.sh; unmapped earner falls back to label'

printf 'Checking stale, missing and unreadable caches show a marker...\n'
write_cache 21:30 "$((NOW - 181))" leetcode:todo:60:22:30
assert_eq '⏻ 20:00 ⏱? 3m' "$(first_line 1200)" 'stale: config time, no cache numbers'
write_cache 21:30 "$((NOW - 180))"
assert_eq '⏻ 21:30' "$(first_line 1200)" '180 s is still fresh'
rm -f "$CACHE"
assert_eq '⏻ 20:00 ⏱?' "$(first_line 1200)" 'missing cache'
printf 'not json\n' >"$CACHE"
rm -f "$RENDER"
assert_eq '⏻ 20:00 ⏱!' "$(first_line 1200)" 'unreadable cache'

printf 'Checking a left-click opens the popup without ~/.local/bin on PATH...\n'
mkdir -p "$TMP_DIR/click-bin"
printf '#!/bin/bash\necho "gui $*" >>"%s/clicks"\n' "$TMP_DIR" >"$TMP_DIR/daily-limits-stub"
printf '#!/bin/bash\necho "notify $*" >>"%s/clicks"\n' "$TMP_DIR" >"$TMP_DIR/click-bin/notify-send"
chmod +x "$TMP_DIR/daily-limits-stub" "$TMP_DIR/click-bin/notify-send"
# i3blocks' PATH has no ~/.local/bin: the launcher must be found by its path.
BLOCK_BUTTON=1 DAILY_LIMITS_BIN="$TMP_DIR/daily-limits-stub" PATH="$TMP_DIR/click-bin:/usr/bin:/bin" first_line 1200 >/dev/null
for _ in 1 2 3 4 5 6 7 8 9 10; do
	[[ -s "$TMP_DIR/clicks" ]] && break
	sleep 0.1
done
assert_eq 'gui --gui' "$(cat "$TMP_DIR/clicks" 2>/dev/null)" 'left-click runs daily-limits --gui'
rm -f "$TMP_DIR/clicks"
# A missing launcher says so instead of a silent no-op.
BLOCK_BUTTON=1 DAILY_LIMITS_BIN="$TMP_DIR/absent" PATH="$TMP_DIR/click-bin:/usr/bin:/bin" first_line 1200 >/dev/null
assert_eq "notify -u critical daily-limits not installed: $TMP_DIR/absent" "$(cat "$TMP_DIR/clicks" 2>/dev/null)" \
	'a missing launcher raises a notification'
rm -f "$TMP_DIR/clicks"

printf 'All shutdown hint tests passed.\n'
