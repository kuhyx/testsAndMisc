#!/bin/bash
# i3blocks persist-mode volume indicator.
#
# Event-driven: blocks in `read` on the `pactl subscribe` event stream.
# No sleep, no polling loop, no awk/tr/grep forks. One pactl-subscribe
# process stays alive; two short pactl calls run only on actual events.
#
# Configure with `interval=persist` in the i3blocks config.

set -u

GREEN='#50FA7B'
RED='#FF5555'

emit() {
  local raw mute vol icon color
  raw=$(pactl get-sink-volume @DEFAULT_SINK@ 2> /dev/null) || return 0
  if [[ $raw =~ ([0-9]+)% ]]; then
    vol=${BASH_REMATCH[1]}
  else
    vol=0
  fi

  mute=$(pactl get-sink-mute @DEFAULT_SINK@ 2> /dev/null) || return 0
  if [[ $mute == *yes ]]; then
    icon='🔇'
    color=$RED
  else
    icon='🔊'
    color=$GREEN
  fi

  printf '%s %s%%\n\n%s\n' "$icon" "$vol" "$color"
}

emit
# `read -r` blocks on the event stream — no busy-wait, no sleep.
pactl subscribe 2> /dev/null | while read -r line; do
  [[ $line == *"on sink"* || $line == *"on server"* ]] || continue
  emit
done
