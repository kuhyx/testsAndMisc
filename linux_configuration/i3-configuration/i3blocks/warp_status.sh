#!/bin/bash
# i3blocks WARP indicator with a single helper process.

set -euo pipefail

if ! command -v warp-cli > /dev/null 2>&1; then
  echo "  N/A"
  exit 0
fi

status=''
while IFS= read -r line; do
  case $line in
    'Status update: '*)
      status=${line#Status update: }
      ;;
  esac
done < <(warp-cli status 2> /dev/null)

if [[ $status == Connected ]]; then
  echo "🔒 !!! WARP CONNECTED !!!"
  echo
  echo "#FFFF00"
elif [[ $status == Disconnected ]]; then
  echo "WARP disconnected"
  echo
  echo "#00FF00"
else
  echo "⚠️ ! WARP unknown !"
  echo
  echo "#FF0000"
fi
