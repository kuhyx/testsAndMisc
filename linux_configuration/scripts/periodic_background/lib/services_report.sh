#!/usr/bin/env bash
# lib/services_report.sh — usage text and the end-of-run status summary table.
#
# Sourced by check_and_enable_services.sh. Reads SERVICE_STATUS, ISSUES_FOUND,
# FIXES_APPLIED, DRY_RUN, STATUS_ONLY and the colour globals from the caller.

usage() {
	cat <<'EOF'
Check and Enable Digital Wellbeing Services
============================================

Usage: sudo ./check_and_enable_services.sh [options]

Options:
  --dry-run    Show what would be done without making changes
  --status     Only show status, don't enable anything
  -h, --help   Show this help message

Services checked:
  1. Pacman wrapper      - Policy-aware pacman wrapper with friction mechanics
  2. Midnight shutdown    - Day-specific automatic shutdown timer
  3. Startup monitor      - PC startup time monitoring service
  4. Periodic systems     - Hourly maintenance timer and hosts monitor
  5. Hosts and guards     - /etc/hosts blocking and protection layers
  6. Compulsive blocker   - Limits messaging apps to one launch per hour
  7. Thorium startup      - Auto-launch Thorium with Fitatu on boot
  8. LeechBlock           - Browser extension for site blocking
  9. Guest mode removal   - Disable Chromium guest mode via policy
 10. VirtualBox hosts     - Enforce /etc/hosts inside VMs
 11. Workout lock screen  - Requires workout logging to unlock screen (user service)
EOF
}

print_summary() {
	header "Summary"

	echo ""
	printf "%-25s %s\n" "Service" "Status"
	printf "%-25s %s\n" "-------" "------"

	for service in pacman_wrapper makepkg_wrapper midnight_shutdown startup_monitor periodic_systems hosts compulsive_blocker leechblock guest_mode_removal vbox_hosts workout_locker; do
		local status
		status="$(get_service_status "$service")"
		local color
		case "$status" in
		ok) color=$GREEN ;;
		warning) color=$YELLOW ;;
		error) color=$RED ;;
		"n/a" | skipped) color=$BLUE ;;
		*) color=$NC ;;
		esac
		printf "%-25s ${color}%s${NC}\n" "$service" "$status"
	done

	echo ""
	if [[ $DRY_RUN -eq 1 ]]; then
		note "DRY RUN - No changes were made"
	fi

	if [[ $ISSUES_FOUND -eq 0 ]]; then
		msg "All services are properly configured!"
	else
		if [[ $STATUS_ONLY -eq 1 ]]; then
			warn "Found $ISSUES_FOUND service(s) with issues"
			note "Run without --status to fix issues"
		else
			if [[ $FIXES_APPLIED -gt 0 ]]; then
				msg "Applied $FIXES_APPLIED fix(es)"
			else
				warn "Found $ISSUES_FOUND issue(s) but no fixes were applied"
			fi
		fi
	fi
}
