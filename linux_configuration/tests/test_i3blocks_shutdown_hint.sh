#!/bin/bash
# Behaviour tests for shutdown_countdown.sh's earner hint: which earners are
# listed, their amounts, the 23:00 ceiling note, and the states that show no
# hint. curl is stubbed on PATH to serve a fixture, so nothing talks to the
# real enforcer.

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
SCHEDULE="$TMP_DIR/schedule.conf"
NO_OVERRIDES="$TMP_DIR/overrides.conf"
: >"$NO_OVERRIDES"
# 2026-05-01 is a Friday, so THU_SUN_MINUTES applies.
NOW=$(TZ=UTC date -d '2026-05-01 18:00:00' +%s)

# write_earners NAME:EARNED:BONUS ... -- the /api/budget earners list.
write_earners() {
	local rows=() name earned bonus
	for spec in "$@"; do
		IFS=: read -r name earned bonus <<<"$spec"
		rows+=("{\"name\":\"$name\",\"label\":\"$name\",\"earned_seconds\":$earned,\"bonus_seconds\":$bonus}")
	done
	local IFS=,
	printf '{"ok":true,"rules":{"earners":[%s]}}\n' "${rows[*]}" >"$FIXTURE"
}

# first_line SHUTDOWN_MINUTES -- the block's full_text at 18:00.
first_line() {
	printf 'THU_SUN_MINUTES=%s\nMON_WED_MINUTES=%s\nMORNING_END_MINUTES=300\n' \
		"$1" "$1" >"$SCHEDULE"
	TZ=UTC NOW_EPOCH="$NOW" PATH="$BIN_DIR:$PATH" FIXTURE="$FIXTURE" \
		SHUTDOWN_CONFIG="$SCHEDULE" OVERRIDES_FILE="$NO_OVERRIDES" \
		SKIP_DATES_FILE=/dev/null bash "$BLOCK" | sed -n 1p
}

printf 'Checking unearned earners are listed with icon and amount...\n'
write_earners workout:7200:7200 leetcode:0:3600 reading:0:3600 anki:0:1800 automation:0:1800
assert_eq '⏻ 20:00 +🧩1h +📖1h +🗂30m +⚙30m' "$(first_line 1200)" \
	'earned ones hidden, the rest listed; 3h fits under 23:00'

printf 'Checking the ceiling note once the bonuses overflow 23:00...\n'
assert_eq '⏻ 22:00 +🧩1h +📖1h +🗂30m +⚙30m →max 23:00' "$(first_line 1320)" \
	'3h of bonuses with 1h of headroom'

printf 'Checking nothing is listed at the ceiling or with all earned...\n'
assert_eq '⏻ 23:00' "$(first_line 1380)" 'no headroom, no hint'
write_earners leetcode:3600:3600 reading:3600:3600
assert_eq '⏻ 20:00' "$(first_line 1200)" 'everything earned'

printf 'Checking odd amounts and unknown earners...\n'
write_earners leetcode:0:5400 newgate:0:900
assert_eq '⏻ 20:00 +🧩1h30 +newgate15m' "$(first_line 1200)" \
	'1h30 padded like gaming_budget.sh; unknown earner falls back to label'

printf 'Checking a dead or unhappy server shows the bare time...\n'
rm -f "$FIXTURE"
assert_eq '⏻ 20:00' "$(first_line 1200)" 'server down'
printf '{"ok":false}\n' >"$FIXTURE"
assert_eq '⏻ 20:00' "$(first_line 1200)" 'budget error'
printf 'not json\n' >"$FIXTURE"
assert_eq '⏻ 20:00' "$(first_line 1200)" 'unreadable reply'

printf 'All shutdown hint tests passed.\n'
