#!/bin/bash
# i3blocks disk usage indicator with a single df helper.

set -euo pipefail

{
  read -r _
  read -r _ size used _
} < <(df -h / 2> /dev/null) || {
  echo "  N/A"
  exit 0
}

echo "  ${used}/${size}"
