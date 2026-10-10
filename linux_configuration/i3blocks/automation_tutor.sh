#!/bin/bash

# ============================================================================
# Automation tutor status for i3blocks: today's credited 15-minute blocks.
#
# A click runs plc-lab's run.sh, which starts the tutor if it is down and
# opens it in the browser -- nobody has to remember the port. Hidden once all
# four blocks are in: nothing left to earn, nothing to click.
#
# Counts the tutor ledger's credit rows dated today. It does not check their
# HMAC (that needs the key and Python); earned_time does, so this is a
# display, never the authority on what was paid.
# ============================================================================

set -euo pipefail

readonly LEDGER="${AUTOMATION_TUTOR_LEDGER:-$HOME/.local/share/automation_tutor/ledger.json}"
# i3blocks' PATH has no ~/src: absolute path.
readonly RUN="${AUTOMATION_TUTOR_RUN:-$HOME/src/plc-lab/run.sh}"
readonly TARGET=4

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
done_blocks=0
# No ledger yet is a real zero: the tutor creates it on the first block.
if [[ -e $LEDGER ]]; then
	if ! done_blocks=$(jq --arg d "$today" \
		'[.entries[] | select(.kind == "credit" and .day == $d)] | length' \
		"$LEDGER" 2>/dev/null); then
		emit '⚙ tutor: ledger unreadable' '⚙ ?' "$ORANGE"
		exit 0
	fi
fi

if ((done_blocks >= TARGET)); then
	emit '' '' "$YELLOW"
	exit 0
fi
emit "⚙ tutor ${done_blocks}/${TARGET}" "⚙ ${done_blocks}/${TARGET}" "$YELLOW"
