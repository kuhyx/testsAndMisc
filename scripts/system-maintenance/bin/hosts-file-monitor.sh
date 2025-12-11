#!/bin/bash
# Hosts file monitor script
# Watches /etc/hosts for changes and restores it if needed
# This file is installed by setup_periodic_system.sh

set -euo pipefail

LOG_FILE="/var/log/hosts-file-monitor.log"
HOSTS_FILE="/etc/hosts"
HOSTS_INSTALL_SCRIPT="__HOSTS_INSTALL_SCRIPT__"

# Log with timestamp (hosts-file-monitor specific)
log_message() {
	printf '%s [hosts-monitor] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$LOG_FILE" >&2
}

# Function to check if hosts file needs restoration
needs_restoration() {
	# Check if file exists
	if [[ ! -f $HOSTS_FILE ]]; then
		return 0 # File missing, needs restoration
	fi

	# Check if file is empty or too small (less than 1000 lines indicates tampering)
	local line_count
	line_count=$(wc -l <"$HOSTS_FILE" 2>/dev/null || echo "0")
	if [[ $line_count -lt 1000 ]]; then
		return 0 # File too small, likely tampered with
	fi

	# Check if our custom entries are missing
	if ! grep -q "Custom blocking entries" "$HOSTS_FILE" 2>/dev/null; then
		return 0 # Our custom entries missing, needs restoration
	fi

	# Check if StevenBlack entries are missing
	if ! grep -q "StevenBlack" "$HOSTS_FILE" 2>/dev/null; then
		return 0 # StevenBlack entries missing, needs restoration
	fi

	return 1 # File seems intact
}

# Function to restore hosts file
restore_hosts_file() {
	log_message "Hosts file modification detected - initiating restoration"

	if [[ -f $HOSTS_INSTALL_SCRIPT ]]; then
		log_message "Running hosts installation script: $HOSTS_INSTALL_SCRIPT"

		if bash "$HOSTS_INSTALL_SCRIPT" >>"$LOG_FILE" 2>&1; then
			log_message "Hosts file restoration completed successfully"
		else
			log_message "Hosts file restoration failed with exit code $?"
		fi
	else
		log_message "ERROR: Hosts install script not found at $HOSTS_INSTALL_SCRIPT"
	fi
}

# Function to monitor with inotifywait
monitor_with_inotify() {
	log_message "Starting hosts file monitoring with inotify"

	# Monitor the hosts file and its directory for various events
	inotifywait -m -e delete,move,modify,attrib,create --format '%w%f %e %T' --timefmt '%Y-%m-%d %H:%M:%S' "$HOSTS_FILE" /etc/ 2>/dev/null |
		while read -r file event time; do
			# Check if the event is related to our hosts file
			if [[ $file == "$HOSTS_FILE" ]] || [[ $file == "/etc/hosts" ]]; then
				log_message "Event detected: $event on $file at $time"

				# Small delay to avoid rapid-fire events
				sleep 2

				# Check if restoration is needed
				if needs_restoration; then
					restore_hosts_file
				else
					log_message "Hosts file check passed - no restoration needed"
				fi
			fi
		done
}

# Function to monitor with polling (fallback)
monitor_with_polling() {
	log_message "Starting hosts file monitoring with polling (fallback method)"

	while true; do
		if needs_restoration; then
			restore_hosts_file
		fi

		# Check every 30 seconds
		sleep 30
	done
}

# Main execution
log_message "=== Hosts File Monitor Started ==="

# Check if inotify-tools is available
if command -v inotifywait >/dev/null 2>&1; then
	log_message "Using inotify for file monitoring"
	monitor_with_inotify
else
	log_message "inotify-tools not available, using polling method"
	log_message "Consider installing inotify-tools for better performance: pacman -S inotify-tools"
	monitor_with_polling
fi
