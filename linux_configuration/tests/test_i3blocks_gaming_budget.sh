#!/bin/bash
# Behaviour tests for the i3blocks gaming_budget block: it renders daily-limits'
# cache ($DAILY_LIMITS_CACHE). Covers text, colour thresholds, the not-done
# earner suffix (todo and unknown), the gaming-day note, the stale/missing/
# garbage states and the "re-parse only when the cache changes" contract.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
BLOCK="$REPO_DIR/i3blocks/gaming_budget.sh"
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
	local expected=$1
	local actual=$2
	local context=$3
	if [[ "$expected" != "$actual" ]]; then
		fail "$context (expected '$expected', actual '$actual')"
	fi
}

printf '{}' | jq -e . >/dev/null 2>&1 ||
	fail 'a working jq is required for the gaming_budget tests (pacman -S jq)'

CACHE="$TMP_DIR/daily-limits.json"
RENDER="$TMP_DIR/render"
NOW=1790000000

# write_cache USED BUDGET GENERATED_AT GAMING_DAY EARNER... where EARNER is
# NAME:STATUS:MINUTES. USED may be "null".
write_cache() {
	local used=$1 budget=$2 generated=$3 day=$4
	shift 4
	local rows=() name status minutes spec
	for spec in "$@"; do
		IFS=: read -r name status minutes <<<"$spec"
		rows+=("{\"name\":\"$name\",\"label\":\"$name\",\"status\":\"$status\",\"shutdown_minutes\":$minutes,\"gaming_minutes\":$minutes}")
	done
	local IFS=,
	printf '{"date":"2026-10-09","generated_at":%s,"shutdown":{"applied":"20:00","resolved":"20:00","floor":"20:00","ceiling":"23:00"},"gaming":{"budget_minutes":%s,"used_minutes":%s,"ceiling_minutes":480,"day":"%s"},"earners":[%s],"todo":[]}\n' \
		"$generated" "$budget" "$used" "$day" "${rows[*]}" >"$CACHE"
	rm -f "$RENDER" # force a re-render for the new content
}
run_block() {
	NOW_EPOCH="$NOW" DAILY_LIMITS_CACHE="$CACHE" DAILY_LIMITS_RENDER_CACHE="$RENDER" bash "$BLOCK"
}

line() {
	run_block | sed -n "${1}p"
}

D=2026-10-09

printf 'Checking the normal day: time left, used/total, not-done bonus...\n'
write_cache 360 480 "$NOW" "$D" workout:done:120 leetcode:done:60 reading:todo:60
assert_eq '🎮 2h00 left · 6h00/8h00 +📖1h' "$(line 1)" 'full text'
assert_eq '🎮 2h00' "$(line 2)" 'short text'
assert_eq '#50FA7B' "$(line 3)" 'green above 1h'

printf 'Checking colour thresholds follow the enforcer warn_at...\n'
write_cache 430 480 "$NOW" "$D" workout:done:120
assert_eq '#F1FA8C' "$(line 3)" 'yellow at <=1h'
assert_eq '🎮 0h50 left · 7h10/8h00' "$(line 1)" 'no suffix when every bonus is earned'
write_cache 460 480 "$NOW" "$D"
assert_eq '#FFB86C' "$(line 3)" 'orange at <=30m'
write_cache 475 480 "$NOW" "$D"
assert_eq '#FF5555' "$(line 3)" 'red at <=10m'

printf 'Checking the blocked state...\n'
write_cache 300 300 "$NOW" "$D" workout:todo:120 leetcode:todo:60 reading:todo:60
assert_eq '🎮 BLOCKED · 5h00/5h00 +💪2h +🧩1h +📖1h' "$(line 1)" 'blocked text lists what can still be earned'
assert_eq '🎮 BLOCKED' "$(line 2)" 'blocked short text'
assert_eq '#FF5555' "$(line 3)" 'blocked is red'
write_cache 302 300 "$NOW" "$D"
assert_eq '🎮 BLOCKED' "$(line 2)" 'overspent counts as blocked'

printf 'Checking earner icons, labels, minutes and the unknown marker...\n'
write_cache 0 240 "$NOW" "$D" workout:done:120 leetcode:todo:60 reading:todo:60 anki:todo:30 automation:todo:30 piano:todo:90
assert_eq '🎮 4h00 left · 0h00/4h00 +🧩1h +📖1h +🗂30m +⚙30m +piano1h30' "$(line 1)" \
	'cache order, done omitted, label for an unmapped earner'
write_cache 0 240 "$NOW" "$D" leetcode:unknown:60 anki:unknown:30 reading:done:60
assert_eq '🎮 4h00 left · 0h00/4h00 +🧩?1h +🗂?30m' "$(line 1)" \
	'unknown earners are shown with a ? marker, not hidden'

printf 'Checking used_minutes null shows only the budget...\n'
write_cache null 180 "$NOW" "$D" leetcode:todo:60
assert_eq '🎮 budget 3h00 +🧩1h' "$(line 1)" 'budget only'
assert_eq '🎮 3h00' "$(line 2)" 'budget only short text'

printf 'Checking the gaming day shows only when it differs from the date...\n'
write_cache 60 180 "$NOW" 2026-10-08 leetcode:todo:60
assert_eq '🎮 2h00 left · 1h00/3h00 (10-08) +🧩1h' "$(line 1)" 'previous gaming day noted'
write_cache 60 180 "$NOW" "$D" leetcode:todo:60
assert_eq '🎮 2h00 left · 1h00/3h00 +🧩1h' "$(line 1)" 'same day: no note'

printf 'Checking a stale or missing cache never shows numbers as fresh...\n'
write_cache 60 180 "$((NOW - 181))" "$D"
assert_eq '🎮 ⏱? stale 3m' "$(line 1)" 'older than 180 s'
assert_eq '#FFB86C' "$(line 3)" 'stale is orange'
write_cache 60 180 "$((NOW - 180))" "$D"
assert_eq '🎮 2h00 left · 1h00/3h00' "$(line 1)" '180 s is still fresh'
rm -f "$CACHE"
assert_eq '🎮 ⏱? no data' "$(line 1)" 'missing cache'
assert_eq '🎮 ⏱?' "$(line 2)" 'missing cache short text'

printf 'Checking an unreadable cache is red...\n'
printf 'not json' >"$CACHE"
rm -f "$RENDER"
assert_eq '🎮 unreadable cache' "$(line 1)" 'garbage body'
assert_eq '#FF5555' "$(line 3)" 'garbage is red'

printf 'Checking jq runs only when the cache file changes...\n'
write_cache 60 180 "$NOW" "$D"
mkdir -p "$TMP_DIR/bin"
printf '#!/bin/bash\necho x >>"%s/jq.calls"\nexec %s "$@"\n' "$TMP_DIR" "$(command -v jq)" >"$TMP_DIR/bin/jq"
chmod +x "$TMP_DIR/bin/jq"
PATH="$TMP_DIR/bin:$PATH" run_block >/dev/null
PATH="$TMP_DIR/bin:$PATH" run_block >/dev/null
assert_eq '1' "$(wc -l <"$TMP_DIR/jq.calls")" 'two ticks, one unchanged cache: one jq run'
sleep 0.05
touch "$CACHE"
PATH="$TMP_DIR/bin:$PATH" run_block >/dev/null
assert_eq '2' "$(wc -l <"$TMP_DIR/jq.calls")" 'a rewritten cache is re-parsed'

printf 'All gaming_budget checks passed.\n'
