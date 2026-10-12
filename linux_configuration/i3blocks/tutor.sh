#!/bin/bash

# ============================================================================
# Tutor status for i3blocks: today's credited tutor minutes.
#
# A click runs ~/src/tutor/run.sh, which starts the tutor if it is down and
# opens it in the browser -- nobody has to remember the port. Hidden once the
# daily cap is in: nothing left to earn, nothing to click.
#
# Sums detail.minutes of the ledger's credit rows dated today (legacy rows
# without it count 15, as earned_time does). It does not check their
# HMAC (that needs the key and Python); earned_time does, so this is a
# display, never the authority on what was paid.
# ============================================================================

set -euo pipefail

readonly LEDGER="${TUTOR_LEDGER:-$HOME/.local/share/tutor/ledger.json}"
# i3blocks' PATH has no ~/src: absolute path.
readonly RUN="${TUTOR_RUN:-$HOME/src/tutor/run.sh}"
readonly TARGET=60 # earned_time daily cap, minutes

readonly YELLOW='#F1FA8C'
readonly ORANGE='#FFB86C'

emit() {
	# full_text, short_text, color — the three lines i3blocks reads.
	printf '%s\n%s\n%s\n' "$1" "$2" "$3"
}

if [[ ${BLOCK_BUTTON:-0} -ne 0 ]]; then
	setsid -f "$RUN" >/dev/null 2>&1 || true
fi

if ! command -v jq >/dev/null 2>&1; then
	emit '⚙ tutor: no jq' '⚙ ?' "$ORANGE"
	exit 0
fi

printf -v today '%(%Y-%m-%d)T' -1
done_minutes=0
# No ledger yet is a real zero: the tutor creates it on the first credit.
if [[ -e $LEDGER ]]; then
	if ! done_minutes=$(jq --arg d "$today" \
		'[.entries[] | select(.kind == "credit" and .day == $d) | (.detail.minutes // 15)] | add // 0 | floor' \
		"$LEDGER" 2>/dev/null); then
		emit '⚙ tutor: ledger unreadable' '⚙ ?' "$ORANGE"
		exit 0
	fi
fi

if ((done_minutes >= TARGET)); then
	emit '' '' "$YELLOW"
	exit 0
fi
emit "⚙ tutor ${done_minutes}/${TARGET}" "⚙ ${done_minutes}/${TARGET}" "$YELLOW"
