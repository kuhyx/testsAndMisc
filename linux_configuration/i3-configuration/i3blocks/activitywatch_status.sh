#!/bin/bash
# ActivityWatch status script for i3blocks.

set -euo pipefail

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

if ! check_installed; then
  echo "AW uninstalled"
  echo
  echo "#FF0000"
elif check_running; then
  echo "AW on"
  echo
  echo "#00FF00"
else
  echo "AW off"
  echo
  echo "#FF0000"
fi
