#!/bin/bash
# Behaviour tests for the i3blocks issue_dashboard block: counts, colours,
# every failure state, the click, and that the hot path forks nothing. The
# status file is a fixture and the launcher a stub, so nothing reads the real
# dashboard state or opens a window.
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
BLOCK="$REPO_DIR/i3blocks/issue_dashboard.sh"
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

BIN_DIR="$TMP_DIR/bin"
mkdir -p "$BIN_DIR"
cat >"$BIN_DIR/launcher" <<STUB
#!/bin/bash
echo clicked >>"$TMP_DIR/clicks"
STUB
chmod +x "$BIN_DIR/launcher"

STATUS="$TMP_DIR/status.json"

# status <todo> <working> <ready> <failed> <age-seconds> [awaiting]
# With no awaiting the file has no "awaiting" key, as an older server writes.
status() {
	local epoch awaiting=''
	printf -v epoch '%(%s)T' -1
	epoch=$((epoch - $5))
	[[ -n ${6:-} ]] && awaiting=", \"awaiting\": $6"
	printf '{"repo": "Sepci0/kado-no-akari", "todo": %s, "working": %s, "ready": %s%s, "failed": %s, "updated": "x", "updated_epoch": %s}\n' \
		"$1" "$2" "$3" "$awaiting" "$4" "$epoch" >"$STATUS"
}

run_block() {
	ISSUE_DASHBOARD_STATUS="$STATUS" ISSUE_DASHBOARD_DESKTOP="$BIN_DIR/launcher" \
		bash "$BLOCK"
}

line() {
	sed -n "${1}p" <<<"$2"
}

printf 'Checking issue_dashboard block states...\n'

status 4 1 0 0 5
out=$(run_block)
assert_eq '📋 4 · ⚙ 1 · ✓ 0' "$(line 1 "$out")" 'fresh text'
assert_eq '📋 4' "$(line 2 "$out")" 'short text'
assert_eq '#FFFFFF' "$(line 3 "$out")" 'nothing to merge is white'

status 4 1 2 0 5
out=$(run_block)
assert_eq '📋 4 · ⚙ 1 · ✓ 2' "$(line 1 "$out")" 'ready text'
assert_eq '#50FA7B' "$(line 3 "$out")" 'something to merge is green'

status 3 0 2 1 5
out=$(run_block)
assert_eq '📋 3 · ⚙ 0 · ✓ 2 · ✗ 1' "$(line 1 "$out")" 'failed text'
assert_eq '#FF5555' "$(line 3 "$out")" 'a failed agent is red'

printf 'Checking merged issues awaiting their opener...\n'

status 3 0 0 0 5 2
out=$(run_block)
assert_eq '📋 3 · ⚙ 0 · ✓ 0 · ⏳ 2' "$(line 1 "$out")" 'awaiting text'
assert_eq '📋 3' "$(line 2 "$out")" 'awaiting stays out of the short text'
assert_eq '#FFFFFF' "$(line 3 "$out")" 'awaiting alone is white'

status 3 0 0 0 5 0
assert_eq '📋 3 · ⚙ 0 · ✓ 0' "$(line 1 "$(run_block)")" 'zero awaiting is hidden'

status 3 0 2 1 5 2
out=$(run_block)
assert_eq '📋 3 · ⚙ 0 · ✓ 2 · ⏳ 2 · ✗ 1' "$(line 1 "$out")" 'awaiting sits between ready and failed'
assert_eq '#FF5555' "$(line 3 "$out")" 'failed still wins the colour'

printf 'Checking failure states are never blank or stale numbers...\n'

status 4 1 2 0 600
out=$(run_block)
assert_eq '📋 dashboard' "$(line 1 "$out")" 'stale status'
assert_eq '#6272A4' "$(line 3 "$out")" 'stale is grey'

rm "$STATUS"
out=$(run_block)
assert_eq '📋 dashboard' "$(line 1 "$out")" 'missing status'
assert_eq '#6272A4' "$(line 3 "$out")" 'missing is grey'

printf '{' >"$STATUS"
assert_eq '📋 dashboard' "$(line 1 "$(run_block)")" 'broken status'
: >"$STATUS"
assert_eq '📋 dashboard' "$(line 1 "$(run_block)")" 'empty status'

printf 'Checking the hot path forks nothing...\n'

status 4 1 2 0 5 1
if command -v strace >/dev/null 2>&1; then
	ISSUE_DASHBOARD_STATUS="$STATUS" strace -f -o "$TMP_DIR/trace" -e trace=execve,clone,clone3,fork,vfork \
		bash "$BLOCK" >/dev/null
	assert_eq '1' "$(grep -c 'execve(' "$TMP_DIR/trace")" 'only bash itself is exec-ed'
	assert_eq '0' "$(grep -cE 'clone3?\(|fork\(' "$TMP_DIR/trace" || true)" 'no child processes'
else
	printf 'strace not installed; skipping the fork count\n'
fi

printf 'Checking a click opens the dashboard window...\n'

BLOCK_BUTTON=1 run_block >/dev/null
for _ in 1 2 3 4 5 6 7 8 9 10; do
	[[ -s "$TMP_DIR/clicks" ]] && break
	sleep 0.1
done
assert_eq 'clicked' "$(cat "$TMP_DIR/clicks" 2>/dev/null)" 'click runs the launcher'

printf 'issue_dashboard block: all checks passed\n'
