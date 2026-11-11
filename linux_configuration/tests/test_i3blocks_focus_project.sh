#!/bin/bash
# Behaviour tests for the i3blocks focus_project block: it renders the `focus`
# field of daily-limits' cache ($DAILY_LIMITS_CACHE). Covers the progress text,
# green once daily_minutes is reached, hidden with no project / no focus key /
# missing, stale or garbage cache, name sanitising, the click, and the
# "re-parse only when the cache changes" contract.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
BLOCK="$REPO_DIR/i3blocks/focus_project.sh"
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
	fail 'a working jq is required for the focus_project tests (pacman -S jq)'

CACHE="$TMP_DIR/daily-limits.json"
RENDER="$TMP_DIR/render"
NOW=1790000000

# write_cache GENERATED_AT FOCUS_JSON  (FOCUS_JSON "" = no focus key at all)
write_cache() {
	local focus=${2:+,\"focus\":$2}
	printf '{"date":"2026-11-02","generated_at":%s%s}\n' "$1" "$focus" >"$CACHE"
	rm -f "$RENDER"
}
focus_json() { # NAME MINUTES DAILY
	jq -nc --arg n "$1" --argjson m "$2" --argjson d "$3" \
		'{project:"p",name:$n,minutes:$m,daily_minutes:$d,unlock_minutes:30,ends:"2026-11-05",replaces:["leetcode"]}'
}
run_block() {
	NOW_EPOCH="$NOW" DAILY_LIMITS_CACHE="$CACHE" DAILY_LIMITS_RENDER_CACHE="$RENDER" \
		DAILY_LIMITS_BIN="$TMP_DIR/dl" bash "$BLOCK"
}
line() { sed -n "${1}p" <<<"$2"; }

printf 'Checking progress and colour...\n'
write_cache "$NOW" "$(focus_json 'HackerRank prep' 45 120)"
out=$(run_block)
assert_eq '🎯 HackerRank prep 45/120' "$(line 1 "$out")" 'full text'
assert_eq '🎯 45/120' "$(line 2 "$out")" 'short text'
assert_eq '#F1FA8C' "$(line 3 "$out")" 'yellow below the daily target'

write_cache "$NOW" "$(focus_json 'HackerRank prep' 120 120)"
out=$(run_block)
assert_eq '🎯 HackerRank prep 120/120' "$(line 1 "$out")" 'target reached text'
assert_eq '#50FA7B' "$(line 3 "$out")" 'green at daily_minutes'

printf 'Checking interview milestones (red when missed, suitcase when a trip question is open)...\n'
RED='#FF5555'
SUITCASE='🧳'
# focus_ms MISSED MINUTES MILESTONE_JSON_ARRAY
focus_ms() {
	jq -nc --argjson x "$1" --argjson m "$2" --argjson ms "$3" \
		'{project:"p",name:"Interview",minutes:$m,daily_minutes:30,missed:$x,milestones:$ms}'
}
ms_json() { # ID STATE
	jq -nc --arg i "$1" --arg s "$2" '[{id:$i,due:"2026-11-12T23:59:00",state:$s}]'
}
write_cache "$NOW" "$(focus_ms true 5 "$(ms_json rules missed)")"
out=$(run_block)
assert_eq "$RED" "$(line 3 "$out")" 'a missed milestone turns the block red'
assert_eq '🎯 Interview 5/30' "$(line 1 "$out")" 'red adds no text'
write_cache "$NOW" "$(focus_ms true 30 "$(ms_json rules missed)")"
assert_eq "$RED" "$(line 3 "$(run_block)")" 'red beats green once the daily target is reached'
write_cache "$NOW" "$(focus_ms false 30 "$(ms_json rules "done")")"
assert_eq '#50FA7B' "$(line 3 "$(run_block)")" 'all milestones done: not red'
write_cache "$NOW" "$(focus_ms false 5 "$(ms_json rules pending)")"
assert_eq '#F1FA8C' "$(line 3 "$(run_block)")" 'only pending milestones: not red'
write_cache "$NOW" "$(focus_json 'No milestones' 5 120)"
assert_eq '#F1FA8C' "$(line 3 "$(run_block)")" 'a project without milestones is not red'
write_cache "$NOW" '{"project":null,"minutes":0,"daily_minutes":0,"missed":true}'
assert_eq '' "$(line 1 "$(run_block)")" 'missed without a project stays hidden'

write_cache "$NOW" "$(focus_ms false 5 "$(ms_json trip_ask:2026-11-14 pending)")"
out=$(run_block)
assert_eq "🎯 Interview 5/30 $SUITCASE" "$(line 1 "$out")" 'pending trip question shows the suitcase'
assert_eq "🎯 5/30 $SUITCASE" "$(line 2 "$out")" 'suitcase in the short text too'
assert_eq '#F1FA8C' "$(line 3 "$out")" 'a pending trip question alone is not red'
write_cache "$NOW" "$(focus_ms true 5 "$(ms_json trip_ask:2026-11-14 missed)")"
out=$(run_block)
assert_eq "🎯 Interview 5/30 $SUITCASE" "$(line 1 "$out")" 'missed trip question shows the suitcase'
assert_eq "$RED" "$(line 3 "$out")" 'missed trip question is red'
for state in "done" late_done; do
	write_cache "$NOW" "$(focus_ms false 5 "$(ms_json trip_ask:2026-11-14 "$state")")"
	assert_eq '🎯 Interview 5/30' "$(line 1 "$(run_block)")" "$state trip question shows no suitcase"
done
write_cache "$NOW" "$(focus_ms false 5 "$(ms_json phone:2026-11-14 pending)")"
assert_eq '🎯 Interview 5/30' "$(line 1 "$(run_block)")" 'other open milestones show no suitcase'

write_cache "$NOW" "$(focus_ms false 5 '["junk",{"id":7},null]')"
assert_eq '🎯 Interview 5/30' "$(line 1 "$(run_block)")" 'malformed milestones are ignored, not fatal'

printf 'Checking the hidden states...\n'
write_cache "$NOW" '{"project":null,"minutes":0,"daily_minutes":0}'
out=$(run_block)
assert_eq '' "$(line 1 "$out")" 'null project hides'
assert_eq '' "$(line 2 "$out")" 'null project hides short text'
write_cache "$NOW" ''
assert_eq '' "$(line 1 "$(run_block)")" 'no focus key hides'
rm -f "$CACHE" "$RENDER"
assert_eq '' "$(line 1 "$(run_block)")" 'missing cache hides (the gaming block says why)'
write_cache $((NOW - 600)) "$(focus_json 'X' 5 120)"
assert_eq '' "$(line 1 "$(run_block)")" 'a stale cache hides, never old numbers'
printf '{' >"$CACHE"
rm -f "$RENDER"
assert_eq '' "$(line 1 "$(run_block)")" 'garbage cache hides'

printf 'Checking a hostile name and a bad daily target...\n'
write_cache "$NOW" "$(focus_json $'Evil\nname<b>' 5 120)"
out=$(run_block)
assert_eq 3 "$(printf '%s\n' "$out" | wc -l)" 'three lines only'
assert_eq '🎯 Evil name<b> 5/120' "$(line 1 "$out")" 'newlines become spaces'
write_cache "$NOW" "$(focus_json 'Z' 5 0)"
assert_eq '#F1FA8C' "$(line 3 "$(run_block)")" 'daily 0 is never green'

printf 'Checking the render cache is reused...\n'
write_cache "$NOW" "$(focus_json 'Keep' 10 120)"
run_block >/dev/null
printf '%s\n' "$NOW" '🎯 CACHED 1/1' '🎯 1/1' '#50FA7B' >"$RENDER"
touch -d '+1 second' "$RENDER"
assert_eq '🎯 CACHED 1/1' "$(line 1 "$(run_block)")" 'unchanged cache is not re-parsed'

printf 'Checking the clicks...\n'
# Stubs record their argv: the block must never open anything for real.
printf '#!/bin/bash\necho "$*" >>"%s/clicks"\n' "$TMP_DIR" >"$TMP_DIR/dl"
printf '#!/bin/bash\necho "py $*" >>"%s/clicks"\n' "$TMP_DIR" >"$TMP_DIR/py"
chmod +x "$TMP_DIR/dl" "$TMP_DIR/py"
click() { # BUTTON -> what the stubs recorded (empty if nothing ran)
	rm -f "$TMP_DIR/clicks"
	BLOCK_BUTTON="$1" FOCUS_OPEN_PYTHON="$TMP_DIR/py" run_block >/dev/null
	for _ in 1 2 3 4 5 6 7 8 9 10; do
		[[ -s "$TMP_DIR/clicks" ]] && break
		sleep 0.1
	done
	cat "$TMP_DIR/clicks" 2>/dev/null || true
}
assert_eq 'py -m focus_project.open' "$(click 1)" 'left click opens the tutor and the work site'
assert_eq 'py -m focus_project.open --no-site' "$(click 2)" 'middle click opens only the tutor'
assert_eq '--gui' "$(click 3)" 'right click opens daily-limits --gui'
assert_eq '' "$(click 0)" 'no click opens nothing'

printf 'focus_project block: all checks passed\n'
