#!/bin/bash
# i3blocks clock, persist mode with zero external helpers in the hot path.

set -uo pipefail

emit() {
  printf '  %(%Y-%m-%d %H:%M)T\n' -1
}

while :; do
  emit
  printf -v now '%(%s)T' -1
  delay=$((60 - now % 60))
  IFS= read -r -t "$delay" _ || true
done
