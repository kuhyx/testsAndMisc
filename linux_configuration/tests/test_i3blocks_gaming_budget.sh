#!/bin/bash
# Behaviour tests for the i3blocks gaming_budget block: text, colour
# thresholds, unearned-bonus suffix and every failure state. curl is stubbed on
# PATH to serve a fixture file, so nothing talks to the real enforcer.

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

# Stub curl: print $FIXTURE, or fail like `curl -f` on a dead server.
BIN_DIR="$TMP_DIR/bin"
mkdir -p "$BIN_DIR"
cat >"$BIN_DIR/curl" <<'STUB'
#!/bin/bash
[[ -r ${FIXTURE:-} ]] || exit 7
cat "$FIXTURE"
STUB
chmod +x "$BIN_DIR/curl"

FIXTURE="$TMP_DIR/budget.json"
CACHE_FILE="$TMP_DIR/cache"
CONFIG_FILE="$TMP_DIR/config.json"

# write_budget USED BUDGET REMAINING BLOCKED WORKOUT LEETCODE READING
write_budget() {
	printf '{"ok":true,"state_status":"ok","today":{"seconds_used":%s,"budget_seconds":%s,"seconds_remaining":%s,"blocked":%s},"rules":{"bonuses":{"base":18000,"workout":%s,"leetcode":%s,"reading":%s}}}\n' \
		"$@" >"$FIXTURE"
}

run_block() {
	PATH="$BIN_DIR:$PATH" FIXTURE="$FIXTURE" GAMING_BUDGET_CACHE="$CACHE_FILE" \
		GAMING_BUDGET_CONFIG="$CONFIG_FILE" bash "$BLOCK"
}

line() {
	run_block | sed -n "${1}p"
}

printf 'Checking the normal day: time left, used/total, missing bonus...\n'
write_budget 21600.3 28800 7199.7 false 7200 3600 0
assert_eq '🎮 2h00 left · 6h00/8h00 +📖1h' "$(line 1)" 'full text'
assert_eq '🎮 2h00' "$(line 2)" 'short text'
assert_eq '#50FA7B' "$(line 3)" 'green above 1h'

printf 'Checking colour thresholds follow the enforcer warn_at...\n'
write_budget 25800 28800 3000 false 7200 3600 3600
assert_eq '#F1FA8C' "$(line 3)" 'yellow at <=1h'
assert_eq '🎮 0h50 left · 7h10/8h00' "$(line 1)" 'no suffix when every bonus is earned'
write_budget 27600 28800 1200 false 7200 3600 3600
assert_eq '#FFB86C' "$(line 3)" 'orange at <=30m'
write_budget 28500 28800 300 false 7200 3600 3600
assert_eq '#FF5555' "$(line 3)" 'red at <=10m'

printf 'Checking the blocked state...\n'
write_budget 18000 18000 0 true 0 0 0
assert_eq '🎮 BLOCKED · 5h00/5h00 +💪2h +🧩1h +📖1h' "$(line 1)" 'blocked full text lists what can still be earned'
assert_eq '🎮 BLOCKED' "$(line 2)" 'blocked short text'
assert_eq '#FF5555' "$(line 3)" 'blocked is red'
write_budget 18100 18000 -100 false 7200 3600 3600
assert_eq '🎮 BLOCKED' "$(line 2)" 'overspent counts as blocked even before the flag flips'

printf 'Checking bonus sizes come from the enforcer config...\n'
printf '{"workout_bonus_seconds":5400,"leetcode_bonus_seconds":0}\n' >"$CONFIG_FILE"
write_budget 0 18000 18000 false 0 0 0
assert_eq '🎮 5h00 left · 0h00/5h00 +💪1h30 +📖1h' "$(line 1)" 'configured sizes, zero-size bonus omitted'
rm -f "$CONFIG_FILE"

printf 'Checking a dead server shows the cached value as stale...\n'
write_budget 21600 28800 7200 false 7200 3600 0
run_block >/dev/null
rm -f "$FIXTURE"
assert_eq '🎮 2h00 left · 6h00/8h00 +📖1h (stale)' "$(line 1)" 'stale text'
assert_eq '#FFB86C' "$(line 3)" 'stale is orange'
rm -f "$CACHE_FILE"
assert_eq '🎮 budget server down' "$(line 1)" 'no cache: server down'
assert_eq '#FF5555' "$(line 3)" 'server down is red'

printf 'Checking error states are red and never overwrite the cache...\n'
printf 'kept' >"$CACHE_FILE"
printf '{"ok":false,"state_status":"corrupt"}\n' >"$FIXTURE"
assert_eq '🎮 state corrupt' "$(line 1)" 'bad state_status'
assert_eq '#FF5555' "$(line 3)" 'bad state is red'
printf '{"ok":false,"state_status":"ok"}\n' >"$FIXTURE"
assert_eq '🎮 budget error' "$(line 1)" 'ok:false'
printf 'not json' >"$FIXTURE"
assert_eq '🎮 unreadable budget' "$(line 1)" 'garbage body'
assert_eq 'kept' "$(<"$CACHE_FILE")" 'error states must leave the cache alone'

printf 'All gaming_budget checks passed.\n'
