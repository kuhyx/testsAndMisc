#!/bin/bash
# i3blocks WARP indicator with a single helper process.

set -euo pipefail

SCRIPT_DIR=${BASH_SOURCE[0]%/*}
[[ $SCRIPT_DIR == "${BASH_SOURCE[0]}" ]] && SCRIPT_DIR='.'
# shellcheck source=linux_configuration/i3-configuration/i3blocks/persist_common.sh
source "$SCRIPT_DIR/persist_common.sh"

if ! command -v warp-cli > /dev/null 2>&1; then
  echo "  N/A"
  exit 0
fi

is_persist_mode() {
  [[ ${BLOCK_INTERVAL:-} == "persist" ]]
}

WARP_POLL_INTERVAL_S=120

read_status() {
  local status line
  status=''
  while IFS= read -r line; do
    case $line in
      'Status update: '*)
        status=${line#Status update: }
        ;;
    esac
  done < <(warp-cli status 2> /dev/null)
  printf '%s\n' "$status"
}

emit_status() {
  local status=$1
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
}

emit_if_changed() {
  local status=$1
  if ! i3blocks_update_if_changed_key "warp_status" "$status"; then
    return 0
  fi
  emit_status "$status"
}

current_status=$(read_status)
emit_status "$current_status"
if is_persist_mode; then
  i3blocks_update_if_changed_key "warp_status" "$current_status" >/dev/null || true
fi
if is_persist_mode; then
  while true; do
    i3blocks_wait_seconds "$WARP_POLL_INTERVAL_S"
    current_status=$(read_status)
    emit_if_changed "$current_status"
  done
fi
