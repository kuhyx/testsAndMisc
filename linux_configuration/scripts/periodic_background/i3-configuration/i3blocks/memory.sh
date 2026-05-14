#!/bin/bash
# i3blocks memory indicator, zero-fork per invocation via /proc/meminfo.

set -euo pipefail

format_mib() {
  local mib=$1
  if ((mib >= 1024)); then
    printf '%d.%dGiB' "$((mib / 1024))" "$((((mib % 1024) * 10) / 1024))"
  else
    printf '%dMiB' "$mib"
  fi
}

total_kib=0
available_kib=0
while IFS=' :' read -r key value _; do
  case $key in
    MemTotal)
      total_kib=$value
      ;;
    MemAvailable)
      available_kib=$value
      ;;
  esac
done < /proc/meminfo

used_mib=$(((total_kib - available_kib) / 1024))
total_mib=$((total_kib / 1024))

printf '  %s/%s\n' "$(format_mib "$used_mib")" "$(format_mib "$total_mib")"
