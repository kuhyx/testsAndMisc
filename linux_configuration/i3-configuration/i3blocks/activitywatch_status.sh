#!/bin/bash
# ActivityWatch status script for i3blocks.

set -euo pipefail

SCRIPT_DIR=${BASH_SOURCE[0]%/*}
[[ $SCRIPT_DIR == "${BASH_SOURCE[0]}" ]] && SCRIPT_DIR='.'
# shellcheck source=linux_configuration/i3-configuration/i3blocks/persist_common.sh
source "$SCRIPT_DIR/persist_common.sh"

check_installed() {
  command -v aw-qt > /dev/null 2>&1 || command -v aw-server > /dev/null 2>&1
}

check_running() {
  local proc_file proc_name
  for proc_file in /proc/[0-9]*/comm; do
    [[ -r $proc_file ]] || continue
    read -r proc_name < "$proc_file" || continue
    case $proc_name in
      aw-qt | aw-server)
        return 0
        ;;
    esac
  done
  return 1
}

emit() {
  local state
  if ! check_installed; then
    state='uninstalled'
  elif check_running; then
    state='on'
  else
    state='off'
  fi

  if ! i3blocks_update_if_changed_key "activitywatch_state" "$state"; then
    return 0
  fi

  if [[ $state == 'uninstalled' ]]; then
    echo "AW uninstalled"
    echo
    echo "#FF0000"
  elif [[ $state == 'on' ]]; then
    echo "AW on"
    echo
    echo "#00FF00"
  else
    echo "AW off"
    echo
    echo "#FF0000"
  fi
}

is_persist_mode() {
  [[ ${BLOCK_INTERVAL:-} == "persist" ]]
}

HEARTBEAT_INTERVAL_S=60

emit

if is_persist_mode; then
  # Intentionally calm heartbeat in persist mode: process-table event streams can
  # be extremely noisy and cause unnecessary churn.
  while true; do
    sleep "$HEARTBEAT_INTERVAL_S"
    emit
  done
fi
