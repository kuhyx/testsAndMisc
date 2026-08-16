#!/usr/bin/env bash
# Formatting, sizing and confirmation helpers for disk_cleanup_check.sh.
#
# Split out to keep the entry script under the 250-line cap. The seam carries
# state deliberately: `report` accumulates into TOTAL_RECLAIMABLE and `confirm`
# reads CLEAN, both owned by the caller. Sourcing this file does not define
# either -- the caller must set them first, which is what keeps the dry-run
# default safe.
#
# shellcheck shell=bash

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

human_readable() {
	local kb=$1
	if ((kb >= 1048576)); then
		printf "%.1f GB" "$(echo "scale=1; $kb / 1048576" | bc)"
	elif ((kb >= 1024)); then
		printf "%.1f MB" "$(echo "scale=1; $kb / 1024" | bc)"
	else
		printf "%d KB" "$kb"
	fi
}

dir_size_kb() {
	local dir="$1"
	if [[ -d "$dir" ]]; then
		du -sk "$dir" 2>/dev/null | awk '{print $1}'
	else
		echo 0
	fi
}

# Prints a row and adds to the caller's TOTAL_RECLAIMABLE. Silent for size 0.
report() {
	local label="$1" size_kb="$2" detail="${3:-}"
	if ((size_kb > 0)); then
		local hr
		hr=$(human_readable "$size_kb")
		printf "${YELLOW}%-40s${RESET} %10s" "$label" "$hr"
		if [[ -n "$detail" ]]; then
			printf "  ${CYAN}(%s)${RESET}" "$detail"
		fi
		printf "\n"
		TOTAL_RECLAIMABLE=$((TOTAL_RECLAIMABLE + size_kb))
	fi
}

# Returns 0 if user confirms, 1 otherwise. Always 1 in dry-run.
confirm() {
	local prompt="$1"
	if $CLEAN; then
		printf "${BOLD}  → %s [y/N]: ${RESET}" "$prompt"
		read -r ans
		if [[ "$ans" =~ ^[Yy]$ ]]; then
			return 0
		fi
	fi
	return 1
}

# Safe wrapper: confirm + action, never fails under errexit
try_clean() {
	local prompt="$1"
	shift
	if confirm "$prompt"; then
		"$@"
		printf "%s  ✓ Done%s\n" "${GREEN}" "${RESET}"
	fi
	return 0
}

# Directories that are never auto-cleaned: too personal to guess at, so they
# are listed with sizes and left alone.
print_report_only() {
	printf "\n%s--- Report-only (manual review needed) ---%s\n" "${BOLD}" "${RESET}"
	local manual_entry dir label size hr
	for manual_entry in \
		"$HOME/Downloads/too_big:~/Downloads/too_big" \
		"$HOME/Downloads:~/Downloads total" \
		"$HOME/inne:~/inne" \
		"/Games:/Games — still playing?"; do
		dir="${manual_entry%%:*}"
		label="${manual_entry#*:}"
		size=$(dir_size_kb "$dir")
		if ((size > 0)); then
			hr=$(human_readable "$size")
			printf "${RED}%-40s %10s${RESET}  ${CYAN}(review manually)${RESET}\n" \
				"$label" "$hr"
		fi
	done
}

# Totals plus a before/after projection against the real filesystem.
print_summary() {
	printf "\n%s\n" "$(printf '%.0s─' {1..60})"
	local total_hr used_kb total_kb used_pct new_used new_pct
	total_hr=$(human_readable "$TOTAL_RECLAIMABLE")
	printf "${BOLD}Total auto-reclaimable:  ${GREEN}%s${RESET}\n" "$total_hr"

	read -r used_kb total_kb used_pct <<<"$(df -k / | awk 'NR==2{print $3, $2, $5}')"
	used_pct="${used_pct%\%}"
	printf "${BOLD}Current usage:           %s / %s (%s%%)${RESET}\n" \
		"$(human_readable "$used_kb")" "$(human_readable "$total_kb")" "$used_pct"

	if ((TOTAL_RECLAIMABLE > 0)); then
		new_used=$((used_kb - TOTAL_RECLAIMABLE))
		if ((new_used < 0)); then new_used=0; fi
		new_pct=$((new_used * 100 / total_kb))
		printf "${BOLD}After cleanup:           %s / %s (%d%%)${RESET}\n" \
			"$(human_readable "$new_used")" "$(human_readable "$total_kb")" "$new_pct"
	fi

	if ! $CLEAN; then
		printf "\n%sRun with --clean to interactively clean each category.%s\n" \
			"${CYAN}" "${RESET}"
	fi
	printf "\n"
}
