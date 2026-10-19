#!/bin/bash
# Behaviour tests for the i3blocks leisure_shadow block: it renders the
# `leisure_shadow` part of daily-limits' cache ($DAILY_LIMITS_CACHE, contract
# C5). Covers text, the yellow/red thresholds, the "no data" states (no cache,
# no key, null numbers), stale/garbage caches, "never urgent" and the
# "re-parse only when the cache changes" contract.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
BLOCK="$REPO_DIR/i3blocks/leisure_shadow.sh"
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
	fail 'a working jq is required for the leisure_shadow tests (pacman -S jq)'

CACHE="$TMP_DIR/daily-limits.json"
RENDER="$TMP_DIR/render"
NOW=1790000000

# write_cache USED BUDGET [GENERATED_AT] -- USED/BUDGET may be "null";
# would_block and left_minutes follow from them as daily-limits writes them.
write_cache() {
	local used=$1 budget=$2 generated=${3:-$NOW} left=null block=false
	if [[ $used != null && $budget != null ]]; then
		left=$((budget > used ? budget - used : 0))
		((used >= budget)) && block=true
	fi
	printf '{"date":"2026-10-19","generated_at":%s,"gaming":{"day":"2026-10-19","budget_minutes":300,"used_minutes":0,"ceiling_minutes":480},"leisure_shadow":{"day":"2026-10-19","budget_minutes":%s,"used_minutes":%s,"left_minutes":%s,"would_block":%s,"sources":[]}}\n' \
		"$generated" "$budget" "$used" "$left" "$block" >"$CACHE"
	rm -f "$RENDER" # force a re-render for the new content
}

run_block() {
	NOW_EPOCH="$NOW" DAILY_LIMITS_CACHE="$CACHE" LEISURE_SHADOW_RENDER_CACHE="$RENDER" bash "$BLOCK"
}

line() {
	run_block | sed -n "${1}p"
}

printf 'Checking the normal day: time left and used...\n'
write_cache 108 300
assert_eq '🛋 SHADOW 3h12 left · 1h48 used' "$(line 1)" 'full text'
assert_eq '🛋 3h12' "$(line 2)" 'short text'
assert_eq '#F8F8F2' "$(line 3)" 'plain foreground above 30 min'
assert_eq '3' "$(run_block | wc -l)" 'exactly full/short/colour, no urgent line'

printf 'Checking yellow strictly under 30 min...\n'
write_cache 270 300
assert_eq '#F8F8F2' "$(line 3)" '30 min left is not yet yellow'
write_cache 271 300
assert_eq '#F1FA8C' "$(line 3)" '29 min left is yellow'
assert_eq '🛋 SHADOW 0h29 left · 4h31 used' "$(line 1)" 'yellow text'
write_cache 299 300
assert_eq '#F1FA8C' "$(line 3)" '1 min left is still yellow, not red'

printf 'Checking would-block at and over 0, never urgent...\n'
write_cache 300 300
assert_eq '🛋 SHADOW WOULD BLOCK · 5h00 used' "$(line 1)" 'at 0'
assert_eq '🛋 WOULD BLOCK' "$(line 2)" 'would-block short text'
assert_eq '#FF5555' "$(line 3)" 'would-block is red'
write_cache 605 600
assert_eq '🛋 SHADOW WOULD BLOCK · 10h05 used' "$(line 1)" 'over'
set +e
run_block >/dev/null
status=$?
set -e
assert_eq '0' "$status" 'exit 0: i3blocks marks exit 33 urgent (flashing)'
assert_eq '3' "$(run_block | wc -l)" 'would-block emits no urgent line'

printf 'Checking "no data" is said, never faked as zero...\n'
write_cache null null
assert_eq '🛋 SHADOW ⏱? no data' "$(line 1)" 'C4 fields absent'
assert_eq '🛋 ⏱?' "$(line 2)" 'no data short text'
assert_eq '#FFB86C' "$(line 3)" 'no data is orange'
printf '{"date":"2026-10-19","generated_at":%s,"gaming":{}}\n' "$NOW" >"$CACHE"
rm -f "$RENDER"
assert_eq '🛋 SHADOW ⏱? no data' "$(line 1)" 'a cache without leisure_shadow'
rm -f "$CACHE"
assert_eq '🛋 SHADOW ⏱? no data' "$(line 1)" 'missing cache'

printf 'Checking a stale or garbage cache...\n'
write_cache 60 300 "$((NOW - 181))"
assert_eq '🛋 SHADOW ⏱? stale 3m' "$(line 1)" 'older than 180 s'
assert_eq '#FFB86C' "$(line 3)" 'stale is orange'
write_cache 60 300 "$((NOW - 180))"
assert_eq '🛋 SHADOW 4h00 left · 1h00 used' "$(line 1)" '180 s is still fresh'
printf 'not json' >"$CACHE"
rm -f "$RENDER"
assert_eq '🛋 SHADOW unreadable cache' "$(line 1)" 'garbage body'
assert_eq '#FF5555' "$(line 3)" 'garbage is red'

printf 'Checking jq runs only when the cache file changes...\n'
write_cache 60 300
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

printf 'Checking the config wires the block next to gaming_budget...\n'
CONFIG="$REPO_DIR/i3blocks/config"
grep -A3 '^\[leisure_shadow\]$' "$CONFIG" | grep -q '^command=~/.config/i3blocks/leisure_shadow.sh$' ||
	fail '[leisure_shadow] should run leisure_shadow.sh'
next_section=$(sed -n '/^\[gaming_budget\]$/,$p' "$CONFIG" | grep -m2 '^\[' | tail -1)
assert_eq '[leisure_shadow]' "$next_section" '[leisure_shadow] sits right after [gaming_budget]'
! grep -A4 '^\[leisure_shadow\]$' "$CONFIG" | grep -q '^urgent' ||
	fail '[leisure_shadow] must never be urgent'

printf 'All leisure_shadow checks passed.\n'
