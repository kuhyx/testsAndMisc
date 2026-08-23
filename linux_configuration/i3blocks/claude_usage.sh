#!/bin/bash
# Claude Code rate-limit status script for i3blocks.
# Shows the 5-hour and 7-day usage windows as percentages.
#
# Data source: ~/.claude/cache/limit-state/*.json, written by the Claude Code
# statusLine hook (~/.claude/scripts/statusline.sh) roughly every 60s while a
# session is open. The cache is sharded one file per project cwd, but the
# limits themselves are ACCOUNT-WIDE - so we read only the most recently
# updated file and ignore its "cwd" field entirely. That keeps this to a
# single file read per tick instead of scanning ~170 files.

set -euo pipefail

LIMIT_STATE_DIR=${LIMIT_STATE_DIR:-$HOME/.claude/cache/limit-state}

# Beyond this age the cached numbers no longer reflect reality, because the
# writer only runs while a Claude session is open. We surface that rather than
# presenting a stale number as current.
STALE_AFTER_S=${STALE_AFTER_S:-900}

ICON='🤖'

readonly COLOR_OK='#50FA7B'
readonly COLOR_WARN='#F1FA8C'
readonly COLOR_CRIT='#FF5555'
readonly COLOR_UNKNOWN='#6272A4'

# i3blocks 3-line protocol: full_text, short_text, color.
emit() {
  printf '%s\n%s\n%s\n' "$1" "$2" "$3"
  exit 0
}

get_now_epoch() {
  if [[ -n ${NOW_EPOCH:-} ]]; then
    printf '%s\n' "$NOW_EPOCH"
  else
    printf '%(%s)T\n' -1
  fi
}

# Newest cache file by mtime. A glob + builtin comparison keeps this fork-free;
# `ls -t | head -1` would spend two processes to answer the same question.
newest_state_file() {
  local candidate newest=''
  for candidate in "$LIMIT_STATE_DIR"/*.json; do
    [[ -f $candidate ]] || continue
    # `-nt` is a bash builtin mtime comparison: it keeps this loop fork-free
    # even though the directory holds one file per project (~170 of them).
    # Calling `stat` here instead would cost a fork per file, every tick.
    if [[ -z $newest ]] || [[ $candidate -nt $newest ]]; then
      newest=$candidate
    fi
  done
  [[ -n $newest ]] || return 1
  printf '%s\n' "$newest"
}

now_epoch=$(get_now_epoch)

if ! state_file=$(newest_state_file); then
  emit "$ICON no data" "$ICON --" "$COLOR_UNKNOWN"
fi

# One jq invocation extracts every field. Percentages are floats in the source
# (e.g. 55.00000000000001), so floor them here; `resets_at` may be null.
if ! fields=$(jq -r '
    [ (.five_hour_pct // "null"),
      (.five_hour_resets_at // "null"),
      (.seven_day_pct // "null"),
      (.seven_day_resets_at // "null"),
      (.updated_at // "null") ]
    | map(if . == "null" then "null" else (. | floor | tostring) end)
    | @tsv' -- "$state_file" 2>/dev/null); then
  emit "$ICON no data" "$ICON --" "$COLOR_UNKNOWN"
fi

IFS=$'\t' read -r five_pct five_resets seven_pct seven_resets updated_at <<<"$fields"

# A window whose reset time has passed has rolled over; the cached percentage
# for it is meaningless, so report unknown rather than a misleading 0%.
window_text() {
  local label=$1 pct=$2 resets=$3
  if [[ $pct == 'null' ]]; then
    printf '%s ?%%' "$label"
    return
  fi
  if [[ $resets != 'null' ]] && [[ $resets -lt $now_epoch ]]; then
    printf '%s ?%%' "$label"
    return
  fi
  printf '%s %s%%' "$label" "$pct"
}

# Colour tracks the window closest to its limit, but only for windows whose
# value is still trustworthy (not rolled over).
worst_pct=-1
consider_pct() {
  local pct=$1 resets=$2
  [[ $pct == 'null' ]] && return 0
  [[ $resets != 'null' ]] && [[ $resets -lt $now_epoch ]] && return 0
  [[ $pct -gt $worst_pct ]] && worst_pct=$pct
  return 0
}

consider_pct "$five_pct" "$five_resets"
consider_pct "$seven_pct" "$seven_resets"

full_text="$ICON $(window_text '5h' "$five_pct" "$five_resets") · $(window_text '7d' "$seven_pct" "$seven_resets")"
short_text="$ICON $(window_text '5h' "$five_pct" "$five_resets")"

# Stale data outranks the usage colouring: the numbers may be arbitrarily old.
if [[ $updated_at == 'null' ]] || [[ $((now_epoch - updated_at)) -gt $STALE_AFTER_S ]]; then
  emit "$full_text (stale)" "$short_text" "$COLOR_UNKNOWN"
fi

if [[ $worst_pct -lt 0 ]]; then
  color=$COLOR_UNKNOWN
elif [[ $worst_pct -ge 85 ]]; then
  color=$COLOR_CRIT
elif [[ $worst_pct -ge 60 ]]; then
  color=$COLOR_WARN
else
  color=$COLOR_OK
fi

emit "$full_text" "$short_text" "$color"
