#!/bin/bash
# Dependency install, apt lock wait and Pi discovery.
#
# Sourced by raspberry_pi_nextcloud.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

wait_for_apt_lock() {
	local max_wait=600
	local waited=0

	while fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock /var/cache/apt/archives/lock >/dev/null 2>&1; do
		if [[ $waited -eq 0 ]]; then
			log_info "Waiting for other apt/dpkg processes to finish..."
			pgrep -a 'apt|dpkg' | head -5 >&2 || true
		fi
		sleep 5
		waited=$((waited + 5))
		if [[ $waited -ge $max_wait ]]; then
			die "Timeout waiting for apt lock after ${max_wait}s"
		fi
		if [[ $((waited % 30)) -eq 0 ]]; then
			log_info "Still waiting... (${waited}s elapsed)"
		fi
	done

	if [[ $waited -gt 0 ]]; then
		log_success "Apt lock acquired after ${waited}s"
	fi
}

# =============================================================================
# Network Discovery (for remote installation)
# =============================================================================

ensure_dependencies() {
	local missing_packages=()

	if ! command -v nmap &>/dev/null; then
		missing_packages+=("nmap")
	fi

	if ! command -v sshpass &>/dev/null; then
		missing_packages+=("sshpass")
	fi

	if [[ ${#missing_packages[@]} -gt 0 ]]; then
		log_info "Installing missing packages: ${missing_packages[*]}"

		if command -v pacman &>/dev/null; then
			sudo pacman -S --noconfirm "${missing_packages[@]}"
		elif command -v apt-get &>/dev/null; then
			sudo apt-get update && sudo apt-get install -y "${missing_packages[@]}"
		elif command -v dnf &>/dev/null; then
			sudo dnf install -y "${missing_packages[@]}"
		else
			die "Could not detect package manager. Please install manually: ${missing_packages[*]}"
		fi
	fi
}

discover_raspberry_pi() {
	log_info "Auto-discovering Raspberry Pi on local network..."

	ensure_dependencies

	local my_ip
	my_ip=$(ip -4 addr show | grep -oP '(?<=inet\s)(?!127\.)\d+(\.\d+){3}' | head -1)
	local gateway
	gateway=$(ip route | grep default | awk '{print $3}' | head -1)
	local network="${gateway%.*}.0/24"

	log_info "Local IP: $my_ip, Network: $network"
	log_info "Scanning for Raspberry Pi (hostname: $PI_HOSTNAME)..."

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

	log_info "Hostname resolution failed, scanning network..."
	nmap -sn -T4 "$network" &>/dev/null || true

	local ssh_hosts
	ssh_hosts=$(nmap -p 22 --open -sT -T4 "$network" 2>/dev/null | grep "Nmap scan report" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -vw "$my_ip" | sort -u) || true

	if [[ -z $ssh_hosts ]]; then
		die "No SSH-enabled devices found. Is the Pi connected and booted?"
	fi

	log_info "Found SSH-enabled devices: $(echo "$ssh_hosts" | tr '\n' ' ')"

	for ip in $ssh_hosts; do
		log_info "Trying $ip with user '$PI_USER'..."

		if sshpass -p "$PI_PASSWORD" ssh -o BatchMode=no -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${PI_USER}@${ip}" "hostname" 2>/dev/null | grep -qi "$PI_HOSTNAME"; then
			log_success "Found Raspberry Pi at $ip"
			echo "$ip"
			return
		fi

		if sshpass -p "$PI_PASSWORD" ssh -o BatchMode=no -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${PI_USER}@${ip}" "echo ok" 2>/dev/null | grep -q "ok"; then
			log_success "Found device responding to Pi credentials at $ip"
			echo "$ip"
			return
		fi
	done

	die "Could not find Raspberry Pi on network."
}
