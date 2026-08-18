#!/bin/bash
# Final run summary for diagnose_pacman_hook_stall.sh.
# Sourced, not executed; inherits the caller's strict mode and globals.

# Print the final transaction summary: counts, per-run durations, and (if any
# stalls happened) the list of captured diagnostic dumps. $1 is a nameref to
# the caller's durations array. Reads RUNS/STALLS/OUT_DIR, all set by main
# before this runs.
print_summary() {
	local -n _durations="$1"

	echo
	echo "============================================================================"
	echo "Summary"
	echo "============================================================================"
	printf '  transactions : %d\n' "$RUNS"
	printf '  stalls       : %d\n' "$STALLS"
	printf '  durations    : %s\n' "${_durations[*]}"
	# Bash, not awk: an inline awk script is opaque to kcov's bash-xtrace
	# based line instrumentation, so those lines stay permanently
	# "uncovered" no matter how thoroughly the code path is exercised.
	# Also guard the count in bash: `printf '%s\n' "${_durations[@]}"` on
	# an empty array still emits one blank line (printf cycles its format
	# at least once), so an awk-side "NR == 0" check was always dead code.
	if ((${#_durations[@]} > 0)); then
		local -a sorted
		mapfile -t sorted < <(printf '%s\n' "${_durations[@]}" | sort -n)
		local count=${#sorted[@]}
		printf '  min/median/max: %ds / %ds / %ds\n' \
			"${sorted[0]}" "${sorted[(count + 1) / 2 - 1]}" "${sorted[count - 1]}"
	fi
	if ((STALLS > 0)); then
		echo
		echo "  Captured dumps:"
		find "$OUT_DIR" -mindepth 1 -maxdepth 1 -type d -printf '    %p\n' \
			2>/dev/null | sort | tail -"$STALLS"
	fi
	echo "============================================================================"
}
