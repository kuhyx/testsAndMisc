#!/bin/bash
set -euo pipefail

REPO="/home/kuhy/src/testsAndMisc"
RUN_SCRIPT="$REPO/run.sh"
OUT_DIR="$HOME/.local/share/usage-reports"
ATOP_DIR="/var/log/atop"

mkdir -p "$OUT_DIR"

if [[ ! -x "$RUN_SCRIPT" ]]; then
	echo "usage-report-catchup: missing executable $RUN_SCRIPT" >&2
	exit 1
fi

shopt -s nullglob
TODAY="$(date +%Y%m%d)"
for atop_file in "$ATOP_DIR"/atop_*; do
	date_part="${atop_file##*_}"
	if [[ ! "$date_part" =~ ^[0-9]{8}$ ]]; then
		continue
	fi

	out_file="$OUT_DIR/usage-report-${date_part}.md"
	tmp_file="$out_file.tmp"

	if [[ "$date_part" == "$TODAY" || ! -s "$out_file" ]]; then
		if "$RUN_SCRIPT" --date "$date_part" >"$tmp_file"; then
			mv -f "$tmp_file" "$out_file"
		else
			rm -f "$tmp_file"
		fi
	fi
done
