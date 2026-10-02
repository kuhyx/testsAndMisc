#!/bin/bash
# Behaviour tests for the i3blocks book_guard block: pace text, colours, every
# failure state and the click. systemctl and the desktop launcher are stubbed,
# and the state file is a fixture, so nothing reads the real Reading folder.
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
BLOCK="$REPO_DIR/i3blocks/book_guard.sh"
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
	fail 'a working jq is required for the book_guard tests (pacman -S jq)'

# Stub systemctl: the timer is active unless TIMER_DOWN is set.
BIN_DIR="$TMP_DIR/bin"
mkdir -p "$BIN_DIR"
cat >"$BIN_DIR/systemctl" <<'STUB'
#!/bin/bash
[[ -z ${TIMER_DOWN:-} ]]
STUB
cat >"$BIN_DIR/launcher" <<STUB
#!/bin/bash
echo clicked >>"$TMP_DIR/clicks"
STUB
chmod +x "$BIN_DIR/systemctl" "$BIN_DIR/launcher"

STATE="$TMP_DIR/state.json"

# state <locked> <pages> <behind> <reason>
state() {
	jq -n --argjson locked "$1" --argjson pages "$2" --argjson behind "$3" \
		--arg reason "$4" \
		'{locked: $locked, reason: $reason,
		  pace: {target: 300, pages: $pages, behind: $behind}}' >"$STATE"
}

run_block() {
	PATH="$BIN_DIR:$PATH" BOOK_GUARD_STATE="$STATE" \
		BOOK_GUARD_DESKTOP="$BIN_DIR/launcher" bash "$BLOCK"
}

line() {
	sed -n "${1}p" <<<"$2"
}

printf 'Checking book_guard block states...\n'

state false 120 0 'on pace'
out=$(run_block)
assert_eq '📖 120/300 ✓' "$(line 1 "$out")" 'on pace text'
assert_eq '📖 120' "$(line 2 "$out")" 'short text'
assert_eq '#50FA7B' "$(line 3 "$out")" 'on pace is green'

state true 40 12 'behind the pace line'
out=$(run_block)
assert_eq '📖 40/300 · LOCKED, 12p behind' "$(line 1 "$out")" 'locked text'
assert_eq '#FF5555' "$(line 3 "$out")" 'locked is red'

state false 0 10 "today's lock was skipped with the escape hatch"
assert_eq '📖 0/300 · 10p behind (escaped)' "$(line 1 "$(run_block)")" 'escaped tag'
state false 0 10 'today is a free day'
assert_eq '📖 0/300 · 10p behind (free day)' "$(line 1 "$(run_block)")" 'free-day tag'
state false 0 10 'before the start date'
out=$(run_block)
assert_eq '📖 0/300 · 10p behind (unlocked)' "$(line 1 "$out")" 'other tag'
assert_eq '#F1FA8C' "$(line 3 "$out")" 'behind but unlocked is yellow'

printf 'Checking failure states are never blank or green...\n'

state false 120 0 'on pace'
touch -d '-2 hours' "$STATE"
out=$(run_block)
assert_eq '📖 120/300 ✓ (stale 120m)' "$(line 1 "$out")" 'stale text'
assert_eq '#FFB86C' "$(line 3 "$out")" 'stale is orange'

state false 120 0 'on pace'
out=$(TIMER_DOWN=1 run_block)
assert_eq '📖 120/300 ✓ ⚠ DISARMED' "$(line 1 "$out")" 'disarmed text'
assert_eq '#FF5555' "$(line 3 "$out")" 'disarmed is red'

rm "$STATE"
out=$(run_block)
assert_eq '📖 no status' "$(line 1 "$out")" 'missing state'
assert_eq '#FFB86C' "$(line 3 "$out")" 'missing is orange'
printf '{' >"$STATE"
assert_eq '📖 no status' "$(line 1 "$(run_block)")" 'broken state'

printf 'Checking a click opens the desktop window...\n'

state false 120 0 'on pace'
BLOCK_BUTTON=1 run_block >/dev/null
for _ in 1 2 3 4 5 6 7 8 9 10; do
	[[ -s "$TMP_DIR/clicks" ]] && break
	sleep 0.1
done
assert_eq 'clicked' "$(cat "$TMP_DIR/clicks" 2>/dev/null)" 'click runs the launcher'

printf 'book_guard block: all checks passed\n'
