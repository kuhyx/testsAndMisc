#!/bin/bash
# Remote host discovery and connection setup.
#
# Sourced by setup_nextcloud_raspberry.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

discover_remote_laptop() {
	log_info "Auto-discovering remote laptop on local network..."

	# Ensure we have the tools we need
	ensure_dependencies

	# Get local IP to exclude ourselves (works on both Linux variants)
	local my_ip
	my_ip=$(ip -4 addr show | grep -oP '(?<=inet\s)(?!127\.)\d+(\.\d+){3}' | head -1)

	# Get gateway
	local gateway
	gateway=$(ip route | grep default | awk '{print $3}' | head -1)
	local network="${gateway%.*}.0/24"

	log_info "Local IP: $my_ip, Gateway: $gateway, Network: $network"

	# Use nmap for fast parallel SSH port scanning
	log_info "Scanning network for SSH-enabled devices (using nmap)..."
	local ssh_hosts
	# First do a ping sweep to wake up hosts, then scan SSH port
	nmap -sn -T4 "$network" &>/dev/null || true
	# Extract IPs from nmap output - grep for report lines then extract IP
	ssh_hosts=$(nmap -p 22 --open -sT -T4 "$network" 2>/dev/null | grep "Nmap scan report" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -vw "$my_ip" | sort -u)

	if [[ -z $ssh_hosts ]]; then
		die "No SSH-enabled devices found on network"
	fi

	local host_count
	host_count=$(echo "$ssh_hosts" | wc -l)
	log_info "Found $host_count SSH-enabled device(s): $(echo "$ssh_hosts" | tr '\n' ' ')"

	# Common usernames to try (in order of preference)
	local common_users=("$REMOTE_LAPTOP_USER" "kuchy" "kuhy" "$(whoami)" "pi" "user" "admin")
	# Remove duplicates while preserving order
	local users=()
	for u in "${common_users[@]}"; do
		local is_dup=0
		for existing in "${users[@]}"; do
			if [[ $u == "$existing" ]]; then
				is_dup=1
				break
			fi
		done
		if [[ $is_dup -eq 0 ]]; then
			users+=("$u")
		fi
	done

	log_info "Will try usernames: ${users[*]}"

	# Find a device with passwordless SSH and SD card
	local found_laptop=""
	local found_user=""
	local idx=0

	for ip in $ssh_hosts; do
		idx=$((idx + 1))

		# Skip gateway
		if [[ $ip == "$gateway" ]]; then
			log_info "[$idx/$host_count] Skipping $ip (gateway)"
			continue
		fi

		log_info "[$idx/$host_count] $ip - Trying SSH key access with common usernames..."

		# Try each username
		for try_user in "${users[@]}"; do
			if ssh -o BatchMode=yes -o ConnectTimeout=2 -o StrictHostKeyChecking=accept-new "${try_user}@${ip}" "echo ok" 2>/dev/null | grep -q "ok"; then
				log_success "[$idx/$host_count] $ip - SSH key access confirmed with user '$try_user'!"
				found_user="$try_user"

				# Check if there's a removable device (SD card)
				log_info "[$idx/$host_count] $ip - Checking for SD card..."
				local has_sd
				has_sd=$(ssh -o BatchMode=yes -o ConnectTimeout=2 "${try_user}@${ip}" "lsblk -d -o NAME,RM,TRAN 2>/dev/null | grep -E '1.*(usb|mmc)' | head -1" 2>/dev/null || true)

				if [[ -n $has_sd ]]; then
					log_success "[$idx/$host_count] $ip - Found SD card: $has_sd"
					found_laptop="$ip"
					break 2 # Break out of both loops
				else
					log_warning "[$idx/$host_count] $ip - No SD card detected, saving as fallback..."
					if [[ -z $found_laptop ]]; then
						found_laptop="$ip"
					fi
				fi
				break # Found working user, move to next IP if no SD card
			fi
		done

		if [[ -z $found_user ]]; then
			log_info "[$idx/$host_count] $ip - No SSH key access with any common username"
		fi
	done

	# If no passwordless access found, prompt user for username
	if [[ -z $found_laptop ]] || [[ -z $found_user ]]; then
		log_warning "No device with passwordless SSH found using common usernames."

		# Pick first available SSH host
		found_laptop=$(echo "$ssh_hosts" | grep -vw "$gateway" | head -1)

		if [[ -z $found_laptop ]]; then
			die "Could not find any suitable SSH-enabled device"
		fi

		log_info "Found SSH host at $found_laptop but need credentials."
		read -r -p "Enter username for $found_laptop: " found_user

		if [[ -z $found_user ]]; then
			die "No username provided"
		fi
	fi

	REMOTE_LAPTOP_IP="$found_laptop"
	REMOTE_LAPTOP_USER="$found_user"
	log_success "Selected remote laptop: ${REMOTE_LAPTOP_USER}@${REMOTE_LAPTOP_IP}"

	# Save to config file for future use
	save_config
}
