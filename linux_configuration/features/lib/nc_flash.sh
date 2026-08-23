#!/bin/bash
# The flash phase, SSH key setup and dependency checks.
#
# Sourced by setup_nextcloud_raspberry.sh; split out to keep nc_image.sh under the
# 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

phase_flash() {
	check_root

	log_info "=== Phase 1: Flash Raspberry Pi OS to SD Card (Local) ==="

	detect_sd_card
	local image_path
	image_path=$(download_raspberry_pi_os)
	flash_sd_card "$image_path"
	configure_headless_boot

	log_success "Phase 1 complete!"
	echo
	log_info "Next steps:"
	log_info "1. Insert the SD card into your Raspberry Pi 5"
	log_info "2. Connect the Pi to power and network"
	log_info "3. Wait 2-3 minutes for first boot"
	log_info "4. Find the Pi's IP address and SSH: ssh ${PI_USER}@<ip-address>"
	log_info "5. Copy this script to the Pi and run: sudo ./setup_nextcloud_raspberry.sh configure"
}

# =============================================================================
# PHASE 1B: Flash Raspberry Pi OS to SD Card on Remote Laptop
# =============================================================================

setup_ssh_key_to_remote() {
	local remote_host="$1"
	local remote_user="$2"

	# Check if we already have passwordless access
	if ssh -o BatchMode=yes -o ConnectTimeout=5 "${remote_user}@${remote_host}" "echo 'SSH key works'" 2>/dev/null; then
		log_success "SSH key authentication to ${remote_user}@${remote_host} already configured"
		return 0
	fi

	log_info "Setting up SSH key authentication to ${remote_user}@${remote_host}..."

	# Check if SSH key exists, if not create one
	if [[ ! -f "$HOME/.ssh/id_ed25519" ]] && [[ ! -f "$HOME/.ssh/id_rsa" ]]; then
		log_info "No SSH key found, generating one..."
		ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -N "" -C "$(whoami)@$(hostname)"
		log_success "SSH key generated"
	fi

	# Copy SSH key to remote host using sshpass if password provided, otherwise prompt
	log_info "Copying SSH key to remote laptop (you will be prompted for password)..."
	ssh-copy-id -o StrictHostKeyChecking=accept-new "${remote_user}@${remote_host}"

	# Verify it works
	if ssh -o BatchMode=yes -o ConnectTimeout=5 "${remote_user}@${remote_host}" "echo 'SSH key works'" 2>/dev/null; then
		log_success "SSH key authentication configured successfully"
		return 0
	else
		die "Failed to set up SSH key authentication"
	fi
}

ensure_dependencies() {
	log_info "Ensuring required tools are installed..."

	local missing_packages=()

	# Check for nmap (fast network scanning)
	if ! command -v nmap &>/dev/null; then
		missing_packages+=("nmap")
	fi

	# Check for sshpass (for initial SSH key setup)
	if ! command -v sshpass &>/dev/null; then
		missing_packages+=("sshpass")
	fi

	if [[ ${#missing_packages[@]} -gt 0 ]]; then
		log_info "Installing missing packages: ${missing_packages[*]}"

		# Detect package manager and install
		if command -v pacman &>/dev/null; then
			sudo pacman -S --noconfirm "${missing_packages[@]}"
		elif command -v apt-get &>/dev/null; then
			sudo apt-get update && sudo apt-get install -y "${missing_packages[@]}"
		elif command -v dnf &>/dev/null; then
			sudo dnf install -y "${missing_packages[@]}"
		elif command -v yum &>/dev/null; then
			sudo yum install -y "${missing_packages[@]}"
		else
			die "Could not detect package manager. Please install manually: ${missing_packages[*]}"
		fi

		log_success "Dependencies installed"
	fi
}
