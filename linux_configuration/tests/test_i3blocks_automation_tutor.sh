#!/bin/bash
# Behaviour tests for the i3blocks automation_tutor block: today's credit
# count, the hidden 4/4 state, the unreadable-ledger warning and the click.
# The ledger is a fixture and run.sh is a stub, so nothing reads the real
# ledger and no tutor or browser is ever started.
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
BLOCK="$REPO_DIR/i3blocks/automation_tutor.sh"
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
	fail 'a working jq is required for the automation_tutor tests (pacman -S jq)'

BIN_DIR="$TMP_DIR/bin"
mkdir -p "$BIN_DIR"
cat >"$BIN_DIR/run.sh" <<STUB
#!/bin/bash
echo clicked >>"$TMP_DIR/clicks"
STUB
chmod +x "$BIN_DIR/run.sh"

LEDGER="$TMP_DIR/ledger.json"

TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d yesterday +%Y-%m-%d)

# ledger <day:kind>...  (writes {"entries":[...]})
ledger() {
	local rows=()
	local spec
	for spec in "$@"; do
		rows+=("$(jq -n --arg day "${spec%%:*}" --arg kind "${spec##*:}" \
			'{day: $day, kind: $kind}')")
	done
	printf '%s\n' "${rows[@]}" | jq -s '{entries: .}' >"$LEDGER"
}

run_block() {
	AUTOMATION_TUTOR_LEDGER="$LEDGER" AUTOMATION_TUTOR_RUN="$BIN_DIR/run.sh" \
		bash "$BLOCK"
}

line() {
	sed -n "${1}p" <<<"$2"
}

printf 'Checking automation_tutor block states...\n'

rm -f "$LEDGER"
out=$(run_block)
assert_eq '⚙ tutor 0/4' "$(line 1 "$out")" 'no ledger is 0/4'
assert_eq '⚙ 0/4' "$(line 2 "$out")" 'no ledger short text'
assert_eq '#F1FA8C' "$(line 3 "$out")" 'progress is yellow'

ledger "$TODAY:credit" "$TODAY:credit" "$YESTERDAY:credit"
out=$(run_block)
assert_eq '⚙ tutor 2/4' "$(line 1 "$out")" 'counts only today'
assert_eq '⚙ 2/4' "$(line 2 "$out")" 'short text'

ledger "$TODAY:credit" "$TODAY:debit"
assert_eq '⚙ tutor 1/4' "$(line 1 "$(run_block)")" 'only credit rows count'

ledger "$TODAY:credit" "$TODAY:credit" "$TODAY:credit" "$TODAY:credit"
out=$(run_block)
assert_eq '' "$(line 1 "$out")" '4/4 hides the block'
assert_eq '' "$(line 2 "$out")" '4/4 short text hidden'

printf 'Checking failure states are never blank or green...\n'

printf '{' >"$LEDGER"
out=$(run_block)
assert_eq '⚙ tutor: ledger unreadable' "$(line 1 "$out")" 'unreadable text'
assert_eq '#FFB86C' "$(line 3 "$out")" 'unreadable is orange'

printf 'Checking a click runs run.sh...\n'

ledger "$TODAY:credit"
BLOCK_BUTTON=1 run_block >/dev/null
for _ in 1 2 3 4 5 6 7 8 9 10; do
	[[ -s "$TMP_DIR/clicks" ]] && break
	sleep 0.1
done
assert_eq 'clicked' "$(cat "$TMP_DIR/clicks" 2>/dev/null)" 'click runs run.sh'

printf 'automation_tutor block: all checks passed\n'
