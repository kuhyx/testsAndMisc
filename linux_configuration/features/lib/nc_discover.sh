#!/bin/bash
# Raspberry Pi discovery on the local network.
#
# Sourced by setup_nextcloud_raspberry.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

# =============================================================================
# PHASE ALL-REMOTE: Configure and install Nextcloud via SSH
# =============================================================================

discover_raspberry_pi() {
	log_info "Auto-discovering Raspberry Pi on local network..."

	ensure_dependencies

	# Get local network info
	local my_ip
	my_ip=$(ip -4 addr show | grep -oP '(?<=inet\s)(?!127\.)\d+(\.\d+){3}' | head -1)
	local gateway
	gateway=$(ip route | grep default | awk '{print $3}' | head -1)
	local network="${gateway%.*}.0/24"

	log_info "Local IP: $my_ip, Network: $network"
	log_info "Scanning for Raspberry Pi (hostname: $PI_HOSTNAME)..."

	# First try to find by hostname
	local pi_ip=""

	# Try resolving hostname directly
	pi_ip=$(getent hosts "$PI_HOSTNAME" 2>/dev/null | awk '{print $1}' | head -1) || true
	if [[ -z $pi_ip ]]; then
		pi_ip=$(getent hosts "${PI_HOSTNAME}.local" 2>/dev/null | awk '{print $1}' | head -1) || true
	fi

	if [[ -n $pi_ip ]]; then
		log_success "Found Pi by hostname: $pi_ip"
		echo "$pi_ip"
		return
	fi

	# Ping sweep to wake up hosts
	log_info "Hostname resolution failed, scanning network..."
	nmap -sn -T4 "$network" &>/dev/null || true

	# Scan for SSH-enabled devices (excluding our IP and known laptop)
	local ssh_hosts
	ssh_hosts=$(nmap -p 22 --open -sT -T4 "$network" 2>/dev/null | grep "Nmap scan report" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -vw "$my_ip" | grep -vw "$REMOTE_LAPTOP_IP" 2>/dev/null | sort -u) || true

	if [[ -z $ssh_hosts ]]; then
		die "No new SSH-enabled devices found. Is the Pi connected and booted?"
	fi

	log_info "Found SSH-enabled devices: $(echo "$ssh_hosts" | tr '\n' ' ')"

	# Try to connect with our Pi credentials
	for ip in $ssh_hosts; do
		log_info "Trying $ip with user '$PI_USER'..."

		# Try with password
		if sshpass -p "$PI_PASSWORD" ssh -o BatchMode=no -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${PI_USER}@${ip}" "hostname" 2>/dev/null | grep -qi "$PI_HOSTNAME"; then
			log_success "Found Raspberry Pi at $ip"
			echo "$ip"
			return
		fi

		# Even if hostname doesn't match, check if it's a fresh Pi responding to our credentials
		if sshpass -p "$PI_PASSWORD" ssh -o BatchMode=no -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${PI_USER}@${ip}" "echo ok" 2>/dev/null | grep -q "ok"; then
			log_success "Found device responding to Pi credentials at $ip"
			echo "$ip"
			return
		fi
	done

	die "Could not find Raspberry Pi on network. Make sure it's connected and has finished booting."
}

phase_all_remote() {
	log_info "=== All-Remote: Configure and Install Nextcloud via SSH ==="

	# Auto-discover Pi IP
	local pi_ip
	pi_ip=$(discover_raspberry_pi)

	if [[ -z $pi_ip ]]; then
		die "Failed to discover Raspberry Pi"
	fi

	log_info "Using Raspberry Pi at: $pi_ip"

	# PI_PASSWORD should already be set from config file
	if [[ -z $PI_PASSWORD ]]; then
		die "PI_PASSWORD not set. Did you run flash-remote first?"
	fi

	# Copy this script to Pi
	log_info "Copying script to Pi..."
	sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no "$0" "${PI_USER}@${pi_ip}:/tmp/setup_nextcloud.sh"

	# Run configuration phase
	log_info "Running configuration phase on Pi..."
	sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI_USER}@${pi_ip}" \
		"echo '$PI_PASSWORD' | sudo -S bash /tmp/setup_nextcloud.sh configure"

	# Run Nextcloud installation phase
	log_info "Running Nextcloud installation on Pi..."

	# Auto-generate Nextcloud admin password if not set
	auto_generate_nextcloud_password
	save_config

	log_success "Nextcloud admin user: $NEXTCLOUD_ADMIN_USER"
	log_success "Nextcloud admin password: $NEXTCLOUD_ADMIN_PASSWORD"

	sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI_USER}@${pi_ip}" \
		"echo '$PI_PASSWORD' | sudo -S NEXTCLOUD_ADMIN_PASSWORD='$NEXTCLOUD_ADMIN_PASSWORD' NEXTCLOUD_ADMIN_USER='$NEXTCLOUD_ADMIN_USER' bash /tmp/setup_nextcloud.sh nextcloud"

	log_success "All-Remote phase complete!"
	echo
	log_info "=== Access Information ==="
	log_info "Nextcloud URL: http://$pi_ip/nextcloud"
	log_info "Admin user: $NEXTCLOUD_ADMIN_USER"
	log_info "Admin password: $NEXTCLOUD_ADMIN_PASSWORD"
	log_info "All credentials saved in: $CONFIG_FILE"
}

# =============================================================================
# MAIN
# =============================================================================

show_help() {
	cat <<'EOF'
Nextcloud on Raspberry Pi 5 Setup Script

Usage: ./setup_nextcloud_raspberry.sh <command>

Commands:
  flash              Flash Raspberry Pi OS to SD card (locally)
  flash-remote       Flash SD card on a remote laptop via SSH
  configure          Configure Pi for remote access (run on Pi after first boot)
  nextcloud          Install and configure Nextcloud (run on Pi)
  all-remote         Run configure + nextcloud via SSH from laptop
  help               Show this help message

Environment Variables (optional):
  PI_HOSTNAME              Hostname for the Pi (default: nextcloud-pi)
  PI_USER                  Username for the Pi (default: pi)
  PI_PASSWORD              Password for Pi user (prompted if not set)
  PI_TIMEZONE              Timezone (default: Europe/Warsaw)
  NEXTCLOUD_ADMIN_USER     Nextcloud admin username (default: admin)
  NEXTCLOUD_ADMIN_PASSWORD Nextcloud admin password (prompted if not set)
  NEXTCLOUD_DATA_DIR       Nextcloud data directory (default: /var/www/nextcloud/data)
  SD_CARD_DEVICE           SD card device path (detected if not set)
  REMOTE_LAPTOP_IP         IP address of remote laptop (default: 192.168.1.17)
  REMOTE_LAPTOP_USER       Username on remote laptop (default: kuhy)

Examples:
  # Flash SD card on a remote laptop in your network
  ./setup_nextcloud_raspberry.sh flash-remote

  # Flash SD card locally
  sudo ./setup_nextcloud_raspberry.sh flash

  # After Pi boots, SSH in and run:
  sudo ./setup_nextcloud_raspberry.sh configure
  sudo ./setup_nextcloud_raspberry.sh nextcloud

  # Or run all phases remotely after flash:
  sudo ./setup_nextcloud_raspberry.sh all-remote
EOF
}
