#!/bin/bash
# Nextcloud on Raspberry Pi 5 Setup Script
# This script handles multiple phases:
# 1. Flash Raspberry Pi OS to SD card (locally or on remote laptop)
# 2. Configure Pi for remote access (run on Pi after first boot)
# 3. Install and configure Nextcloud (run on Pi)
#
# Usage:
#   ./setup_nextcloud_raspberry.sh flash            - Flash SD card locally
#   ./setup_nextcloud_raspberry.sh flash-remote     - Flash SD card on remote laptop via SSH
#   ./setup_nextcloud_raspberry.sh configure        - Configure Pi for remote access (run on Pi)
#   ./setup_nextcloud_raspberry.sh nextcloud        - Install Nextcloud (run on Pi)
#   ./setup_nextcloud_raspberry.sh all-remote       - Run configure + nextcloud via SSH

set -euo pipefail

# Script directory for config file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/.nextcloud_raspberry.conf"

# Load configuration from gitignored config file if it exists
if [[ -f $CONFIG_FILE ]]; then
	# shellcheck source=/dev/null
	source "$CONFIG_FILE"
fi

# Configuration - Customize these values (or set in config file)
PI_HOSTNAME="${PI_HOSTNAME:-nextcloud-pi}"
PI_USER="${PI_USER:-pi}"
PI_PASSWORD="${PI_PASSWORD:-}" # Leave empty to be prompted
PI_TIMEZONE="${PI_TIMEZONE:-Europe/Warsaw}"
PI_LOCALE="${PI_LOCALE:-en_US.UTF-8}"
NEXTCLOUD_ADMIN_USER="${NEXTCLOUD_ADMIN_USER:-admin}"
NEXTCLOUD_ADMIN_PASSWORD="${NEXTCLOUD_ADMIN_PASSWORD:-}" # Leave empty to be prompted
NEXTCLOUD_DATA_DIR="${NEXTCLOUD_DATA_DIR:-/var/www/nextcloud/data}"
SD_CARD_DEVICE="${SD_CARD_DEVICE:-}" # e.g., /dev/sdb - will be detected if empty

# Remote laptop configuration - will be auto-discovered if not set
# Default to kuchy for the remote laptop, can be overridden via config file
REMOTE_LAPTOP_USER="${REMOTE_LAPTOP_USER:-kuchy}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# All log functions output to stderr so they don't interfere with function return values
log_info() {
	echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
	echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
	echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
	echo -e "${RED}[ERROR]${NC} $1" >&2
}

die() {
	log_error "$1"
	exit 1
}

check_root() {
	if [[ $EUID -ne 0 ]]; then
		die "This script must be run as root. Use: sudo $0"
	fi
}

save_config() {
	# Save discovered/used configuration to gitignored config file
	cat >"$CONFIG_FILE" <<EOF
# Nextcloud Raspberry Pi Setup - Auto-generated config
# This file is gitignored and stores discovered settings

# Remote laptop (auto-discovered)
REMOTE_LAPTOP_USER="${REMOTE_LAPTOP_USER}"

# Pi configuration
PI_HOSTNAME="${PI_HOSTNAME}"
PI_USER="${PI_USER}"
PI_TIMEZONE="${PI_TIMEZONE}"
NEXTCLOUD_ADMIN_USER="${NEXTCLOUD_ADMIN_USER}"

# Generated passwords (KEEP THIS FILE SECURE!)
PI_PASSWORD="${PI_PASSWORD}"
NEXTCLOUD_ADMIN_PASSWORD="${NEXTCLOUD_ADMIN_PASSWORD}"
EOF
	chmod 600 "$CONFIG_FILE"
	log_info "Configuration saved to $CONFIG_FILE"
}

generate_password() {
	# Generate a secure random password (16 chars, alphanumeric + some symbols)
	local length="${1:-16}"
	# Use /dev/urandom for randomness, base64 encode, take first N chars
	# Using dd to avoid SIGPIPE with pipefail
	local chars
	chars=$(dd if=/dev/urandom bs=256 count=1 2>/dev/null | tr -dc 'A-Za-z0-9!@#$%&*' | cut -c1-"$length")
	echo "$chars"
}

auto_generate_pi_password() {
	if [[ -z $PI_PASSWORD ]]; then
		PI_PASSWORD=$(generate_password 16)
		log_info "Auto-generated Pi password (will be saved to config file)"
	fi
}

auto_generate_nextcloud_password() {
	if [[ -z $NEXTCLOUD_ADMIN_PASSWORD ]]; then
		NEXTCLOUD_ADMIN_PASSWORD=$(generate_password 20)
		log_info "Auto-generated Nextcloud admin password (will be saved to config file)"
	fi
}

prompt_password() {
	local prompt="$1"
	local var_name="$2"
	local password=""
	local password_confirm=""

	while true; do
		read -r -s -p "$prompt: " password
		echo
		read -r -s -p "Confirm password: " password_confirm
		echo

		if [[ $password == "$password_confirm" ]]; then
			if [[ -z $password ]]; then
				log_warning "Password cannot be empty. Please try again."
				continue
			fi
			eval "$var_name='$password'"
			break
		else
			log_warning "Passwords do not match. Please try again."
		fi
	done
}

# =============================================================================
# PHASE 1: Flash Raspberry Pi OS to SD Card
# =============================================================================

detect_sd_card() {
	log_info "Detecting removable storage devices..."

	# List block devices that are removable
	local devices
	devices=$(lsblk -d -o NAME,SIZE,TYPE,RM,TRAN | grep -E "disk.*1.*usb|disk.*1.*mmc" | awk '{print "/dev/"$1" ("$2")"}')

	if [[ -z $devices ]]; then
		log_warning "No removable devices detected automatically."
		log_info "Available block devices:"
		lsblk -d -o NAME,SIZE,TYPE,RM,TRAN
		echo
		read -r -p "Enter the SD card device path (e.g., /dev/sdb): " SD_CARD_DEVICE
	else
		echo "Detected removable devices:"
		echo "$devices"
		echo
		read -r -p "Enter the SD card device path from above (e.g., /dev/sdb): " SD_CARD_DEVICE
	fi

	# Validate device exists
	if [[ ! -b $SD_CARD_DEVICE ]]; then
		die "Device $SD_CARD_DEVICE does not exist or is not a block device"
	fi

	# Safety check - don't flash system drive
	local root_device
	root_device=$(findmnt -n -o SOURCE / | sed 's/[0-9]*$//' | sed 's/p[0-9]*$//')
	if [[ $SD_CARD_DEVICE == "$root_device" ]]; then
		die "Cannot flash to the system drive!"
	fi
}

download_raspberry_pi_os() {
	local download_dir="/tmp/rpi-image"
	local image_url="https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2024-11-19/2024-11-19-raspios-bookworm-arm64-lite.img.xz"
	local image_file="$download_dir/raspios.img.xz"
	local extracted_image="$download_dir/raspios.img"
	local expected_size=459000608 # Size in bytes from content-length

	mkdir -p "$download_dir"

	if [[ -f $extracted_image ]]; then
		log_info "Using existing image at $extracted_image"
		echo "$extracted_image"
		return
	fi

	# Check if download exists and is complete
	if [[ -f $image_file ]]; then
		local actual_size
		actual_size=$(stat -c%s "$image_file" 2>/dev/null || stat -f%z "$image_file" 2>/dev/null || echo 0)
		if [[ $actual_size -lt $expected_size ]]; then
			log_warning "Incomplete download detected ($actual_size < $expected_size bytes), re-downloading..."
			rm -f "$image_file"
		else
			log_info "Image archive already downloaded"
		fi
	fi

	if [[ ! -f $image_file ]]; then
		log_info "Downloading Raspberry Pi OS Lite (64-bit)..."
		log_info "This may take a while depending on your internet connection..."

		# Try to use aria2c for faster download, fall back to wget/curl
		# Redirect all output to stderr so it doesn't interfere with function return value
		if command -v aria2c &>/dev/null; then
			aria2c -x 4 -c -d "$download_dir" --out="raspios.img.xz" "$image_url" >&2
		elif command -v wget &>/dev/null; then
			wget --continue --show-progress -O "$image_file" "$image_url" >&2
		elif command -v curl &>/dev/null; then
			curl -L -C - -o "$image_file" "$image_url" --progress-bar >&2
		else
			die "No download tool available. Install wget, curl, or aria2c"
		fi

		# Verify download size
		local actual_size
		actual_size=$(stat -c%s "$image_file" 2>/dev/null || stat -f%z "$image_file" 2>/dev/null || echo 0)
		if [[ $actual_size -lt $expected_size ]]; then
			die "Download incomplete: got $actual_size bytes, expected $expected_size"
		fi
		log_success "Download complete: $actual_size bytes"
	fi

	log_info "Extracting image..."
	xz -dk "$image_file"

	if [[ ! -f $extracted_image ]]; then
		die "Failed to extract image"
	fi

	echo "$extracted_image"
}

flash_sd_card() {
	local image_path="$1"

	log_warning "This will ERASE ALL DATA on $SD_CARD_DEVICE"
	read -r -p "Are you sure you want to continue? (yes/no): " confirm

	if [[ $confirm != "yes" ]]; then
		die "Aborted by user"
	fi

	# Unmount any mounted partitions
	log_info "Unmounting partitions on $SD_CARD_DEVICE..."
	for partition in "${SD_CARD_DEVICE}"*; do
		if mountpoint -q "$partition" 2>/dev/null || mount | grep -q "$partition"; then
			umount "$partition" 2>/dev/null || true
		fi
	done

	log_info "Flashing image to SD card..."
	log_info "This will take several minutes..."

	dd if="$image_path" of="$SD_CARD_DEVICE" bs=4M status=progress conv=fsync

	sync
	log_success "Image flashed successfully!"
}

configure_headless_boot() {
	log_info "Configuring headless boot (SSH and WiFi)..."

	# Wait for partitions to be available
	sleep 2
	partprobe "$SD_CARD_DEVICE" 2>/dev/null || true
	sleep 2

	# Mount boot partition
	local boot_partition
	if [[ -b "${SD_CARD_DEVICE}1" ]]; then
		boot_partition="${SD_CARD_DEVICE}1"
	elif [[ -b "${SD_CARD_DEVICE}p1" ]]; then
		boot_partition="${SD_CARD_DEVICE}p1"
	else
		die "Could not find boot partition"
	fi

	local boot_mount="/tmp/rpi-boot"
	mkdir -p "$boot_mount"
	mount "$boot_partition" "$boot_mount"

	# Enable SSH
	touch "$boot_mount/ssh"
	log_success "SSH enabled"

	# Configure WiFi (optional)
	read -r -p "Do you want to configure WiFi? (y/n): " configure_wifi
	if [[ $configure_wifi == "y" ]]; then
		read -r -p "WiFi SSID: " wifi_ssid
		read -r -s -p "WiFi Password: " wifi_password
		echo

		cat >"$boot_mount/wpa_supplicant.conf" <<EOF
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="$wifi_ssid"
    psk="$wifi_password"
    key_mgmt=WPA-PSK
}
EOF
		log_success "WiFi configured"
	fi

	# Create userconf.txt for first user (Raspberry Pi OS Bookworm+)
	if [[ -z $PI_PASSWORD ]]; then
		prompt_password "Enter password for Pi user '$PI_USER'" PI_PASSWORD
	fi

	local encrypted_password
	encrypted_password=$(echo "$PI_PASSWORD" | openssl passwd -6 -stdin)
	echo "${PI_USER}:${encrypted_password}" >"$boot_mount/userconf.txt"
	log_success "User '$PI_USER' configured"

	# Set hostname
	local root_partition
	if [[ -b "${SD_CARD_DEVICE}2" ]]; then
		root_partition="${SD_CARD_DEVICE}2"
	elif [[ -b "${SD_CARD_DEVICE}p2" ]]; then
		root_partition="${SD_CARD_DEVICE}p2"
	fi

	if [[ -n $root_partition ]]; then
		local root_mount="/tmp/rpi-root"
		mkdir -p "$root_mount"
		mount "$root_partition" "$root_mount"

		echo "$PI_HOSTNAME" >"$root_mount/etc/hostname"
		sed -i "s/raspberrypi/$PI_HOSTNAME/g" "$root_mount/etc/hosts"

		log_success "Hostname set to '$PI_HOSTNAME'"

		umount "$root_mount"
	fi

	umount "$boot_mount"

	log_success "SD card configured for headless boot!"
	log_info "Insert the SD card into your Raspberry Pi and power it on."
	log_info "Find the Pi's IP address from your router or use: nmap -sn 192.168.1.0/24"
}

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

phase_flash_remote() {
	log_info "=== Phase 1B: Flash Raspberry Pi OS to SD Card on Remote Laptop ==="

	# Discover and select remote laptop
	discover_remote_laptop

	# Set up SSH key authentication
	setup_ssh_key_to_remote "$REMOTE_LAPTOP_IP" "$REMOTE_LAPTOP_USER"

	local remote="${REMOTE_LAPTOP_USER}@${REMOTE_LAPTOP_IP}"

	# Check for SD card on remote laptop
	log_info "Checking for SD card on remote laptop..."
	echo "Block devices on ${remote}:"
	ssh "$remote" "lsblk -d -o NAME,SIZE,TYPE,RM,TRAN,MODEL" || true
	echo

	# Auto-detect SD card on remote laptop
	log_info "Auto-detecting SD card on remote laptop..."
	local sd_device
	sd_device=$(ssh "$remote" "lsblk -d -o NAME,RM,TRAN | grep -E '1.*(usb|mmc)' | awk '{print \"/dev/\"\$1}' | head -1" 2>/dev/null || true)

	if [[ -z $sd_device ]]; then
		die "No SD card detected on remote laptop. Please insert an SD card and try again."
	fi

	# Get size for confirmation
	local sd_info
	# shellcheck disable=SC2029  # Intentional client-side expansion
	sd_info=$(ssh "$remote" "lsblk -d -o NAME,SIZE,MODEL $sd_device 2>/dev/null | tail -1" || true)

	log_success "Auto-detected SD card: $sd_device ($sd_info)"
	SD_CARD_DEVICE="$sd_device"

	# Verify device exists on remote
	# shellcheck disable=SC2029  # Intentional client-side expansion
	if ! ssh "$remote" "[[ -b '$SD_CARD_DEVICE' ]]" 2>/dev/null; then
		die "Device $SD_CARD_DEVICE does not exist on remote laptop"
	fi

	# Auto-generate Pi password if not set
	auto_generate_pi_password
	log_success "Pi user '$PI_USER' password: $PI_PASSWORD"

	# Generate encrypted password locally
	local encrypted_password
	encrypted_password=$(echo "$PI_PASSWORD" | openssl passwd -6 -stdin)

	# Save config now so password is stored
	save_config

	# Copy this script to remote laptop
	log_info "Copying script to remote laptop..."
	scp "$0" "${remote}:/tmp/setup_nextcloud_raspberry.sh"

	# Execute flash on remote laptop
	log_info "Executing flash on remote laptop..."
	log_warning "This will ERASE ALL DATA on ${SD_CARD_DEVICE} on the remote laptop!"
	log_info "Proceeding automatically in 5 seconds... (Ctrl+C to cancel)"
	sleep 5

	# Run the flash process on remote laptop
	# We pass the pre-encrypted password to avoid interactive prompts
	# Using -tt to force TTY allocation even without local tty
	ssh -tt "$remote" "sudo SD_CARD_DEVICE='$SD_CARD_DEVICE' PI_USER='$PI_USER' PI_HOSTNAME='$PI_HOSTNAME' bash /tmp/setup_nextcloud_raspberry.sh flash-remote-execute '$encrypted_password'"

	log_success "Phase 1B complete!"
	echo
	log_info "Next steps:"
	log_info "1. Remove SD card from the laptop and insert into Raspberry Pi 5"
	log_info "2. Connect the Pi to power and network"
	log_info "3. Wait 2-3 minutes for first boot"
	log_info "4. Run: ./setup_nextcloud_raspberry.sh configure (on Pi) or all-remote"
}

# This is called on the remote laptop by phase_flash_remote
phase_flash_remote_execute() {
	check_root

	local encrypted_password="${1:-}"

	log_info "=== Executing Flash on Remote Laptop ==="

	if [[ -z $SD_CARD_DEVICE ]]; then
		die "SD_CARD_DEVICE not set"
	fi

	# Download and flash
	local image_path
	image_path=$(download_raspberry_pi_os)

	# Unmount any mounted partitions
	log_info "Unmounting partitions on $SD_CARD_DEVICE..."
	for partition in "${SD_CARD_DEVICE}"*; do
		if mountpoint -q "$partition" 2>/dev/null || mount | grep -q "$partition"; then
			umount "$partition" 2>/dev/null || true
		fi
	done

	log_info "Flashing image to SD card..."
	dd if="$image_path" of="$SD_CARD_DEVICE" bs=4M status=progress conv=fsync
	sync
	log_success "Image flashed successfully!"

	# Configure headless boot
	log_info "Configuring headless boot..."
	sleep 2
	partprobe "$SD_CARD_DEVICE" 2>/dev/null || true
	sleep 2

	# Mount boot partition
	local boot_partition
	if [[ -b "${SD_CARD_DEVICE}1" ]]; then
		boot_partition="${SD_CARD_DEVICE}1"
	elif [[ -b "${SD_CARD_DEVICE}p1" ]]; then
		boot_partition="${SD_CARD_DEVICE}p1"
	else
		die "Could not find boot partition"
	fi

	local boot_mount="/tmp/rpi-boot"
	mkdir -p "$boot_mount"
	mount "$boot_partition" "$boot_mount"

	# Enable SSH
	touch "$boot_mount/ssh"
	log_success "SSH enabled"

	# Create userconf.txt for first user
	if [[ -n $encrypted_password ]]; then
		echo "${PI_USER}:${encrypted_password}" >"$boot_mount/userconf.txt"
		log_success "User '$PI_USER' configured"
	fi

	# Set hostname on root partition
	local root_partition
	if [[ -b "${SD_CARD_DEVICE}2" ]]; then
		root_partition="${SD_CARD_DEVICE}2"
	elif [[ -b "${SD_CARD_DEVICE}p2" ]]; then
		root_partition="${SD_CARD_DEVICE}p2"
	fi

	if [[ -n $root_partition ]]; then
		local root_mount="/tmp/rpi-root"
		mkdir -p "$root_mount"
		mount "$root_partition" "$root_mount"

		echo "$PI_HOSTNAME" >"$root_mount/etc/hostname"
		sed -i "s/raspberrypi/$PI_HOSTNAME/g" "$root_mount/etc/hosts"

		log_success "Hostname set to '$PI_HOSTNAME'"

		umount "$root_mount"
	fi

	umount "$boot_mount"
	sync

	log_success "SD card configured for headless boot!"
}

# =============================================================================
# PHASE 2: Configure Pi for Remote Access
# =============================================================================

wait_for_apt_lock() {
	# Wait for any existing apt/dpkg processes to finish
	local max_wait=600 # 10 minutes max
	local waited=0

	while fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock /var/cache/apt/archives/lock >/dev/null 2>&1; do
		if [[ $waited -eq 0 ]]; then
			log_info "Waiting for other apt/dpkg processes to finish..."
			log_info "Current apt processes:"
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

phase_configure() {
	check_root

	log_info "=== Phase 2: Configure Raspberry Pi for Remote Access ==="

	# Wait for any existing apt processes
	wait_for_apt_lock

	# Fix any broken packages first
	log_info "Fixing any broken packages..."
	DEBIAN_FRONTEND=noninteractive dpkg --configure -a --force-confdef --force-confold || true

	# Update system - use non-interactive mode and auto-accept config changes
	log_info "Updating system packages..."
	apt-get update
	DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade -y

	# Set timezone
	log_info "Setting timezone to $PI_TIMEZONE..."
	timedatectl set-timezone "$PI_TIMEZONE"

	# Set locale
	log_info "Configuring locale..."
	sed -i "s/^# *$PI_LOCALE/$PI_LOCALE/" /etc/locale.gen
	locale-gen
	update-locale LANG="$PI_LOCALE"

	# Configure SSH for security
	log_info "Hardening SSH configuration..."

	# Backup original config
	cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

	# Apply security settings
	cat >>/etc/ssh/sshd_config.d/hardening.conf <<'EOF'
# Security hardening
PermitRootLogin no
PasswordAuthentication yes
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

	# Restart SSH
	systemctl restart sshd

	# Install useful packages
	log_info "Installing useful packages..."
	apt-get install -y \
		vim \
		htop \
		curl \
		wget \
		git \
		ufw \
		fail2ban \
		unattended-upgrades

	# Configure firewall
	log_info "Configuring firewall..."
	ufw default deny incoming
	ufw default allow outgoing
	ufw allow ssh
	ufw allow 80/tcp  # HTTP
	ufw allow 443/tcp # HTTPS
	ufw --force enable

	# Configure fail2ban
	log_info "Configuring fail2ban..."
	cat >/etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

	systemctl enable fail2ban
	systemctl restart fail2ban

	# Enable automatic security updates
	log_info "Enabling automatic security updates..."
	cat >/etc/apt/apt.conf.d/50unattended-upgrades <<'EOF'
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=${distro_codename},label=Debian-Security";
    "origin=Raspbian,codename=${distro_codename},label=Raspbian";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF

	systemctl enable unattended-upgrades

	# Display system info
	log_info "System information:"
	echo "Hostname: $(hostname)"
	echo "IP Address: $(hostname -I | awk '{print $1}')"
	echo "Kernel: $(uname -r)"
	echo "Architecture: $(uname -m)"

	log_success "Phase 2 complete!"
	echo
	log_info "Next step: Run 'sudo ./setup_nextcloud_raspberry.sh nextcloud' to install Nextcloud"
}

# =============================================================================
# PHASE 3: Install Nextcloud
# =============================================================================

install_nextcloud_dependencies() {
	log_info "Installing Nextcloud dependencies..."

	apt-get update
	apt-get install -y \
		apache2 \
		mariadb-server \
		libapache2-mod-php \
		php \
		php-gd \
		php-mysql \
		php-curl \
		php-mbstring \
		php-intl \
		php-gmp \
		php-bcmath \
		php-xml \
		php-zip \
		php-imagick \
		php-apcu \
		php-redis \
		redis-server \
		unzip \
		certbot \
		python3-certbot-apache

	log_success "Dependencies installed"
}

configure_mariadb() {
	log_info "Configuring MariaDB..."

	# Generate random password for Nextcloud DB user
	local db_password
	db_password=$(openssl rand -base64 24)

	# Start and enable MariaDB
	systemctl start mariadb
	systemctl enable mariadb

	# Secure MariaDB installation
	mysql -e "DELETE FROM mysql.user WHERE User='';"
	mysql -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
	mysql -e "DROP DATABASE IF EXISTS test;"
	mysql -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"
	mysql -e "FLUSH PRIVILEGES;"

	# Create Nextcloud database and user
	mysql -e "CREATE DATABASE IF NOT EXISTS nextcloud CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
	mysql -e "CREATE USER IF NOT EXISTS 'nextcloud'@'localhost' IDENTIFIED BY '$db_password';"
	mysql -e "GRANT ALL PRIVILEGES ON nextcloud.* TO 'nextcloud'@'localhost';"
	mysql -e "FLUSH PRIVILEGES;"

	# Save password for later use
	echo "$db_password" >/root/.nextcloud_db_password
	chmod 600 /root/.nextcloud_db_password

	log_success "MariaDB configured"
	echo "$db_password"
}

download_nextcloud() {
	log_info "Downloading Nextcloud..."

	local nc_version="30.0.2"
	local nc_url="https://download.nextcloud.com/server/releases/nextcloud-${nc_version}.zip"
	local download_dir="/tmp"
	local nc_zip="$download_dir/nextcloud.zip"

	if [[ -f $nc_zip ]]; then
		log_info "Nextcloud archive already downloaded"
	else
		wget -O "$nc_zip" "$nc_url"
	fi

	# Remove existing installation if present
	rm -rf /var/www/nextcloud

	# Extract
	unzip -q "$nc_zip" -d /var/www/

	# Set permissions
	chown -R www-data:www-data /var/www/nextcloud

	log_success "Nextcloud downloaded and extracted"
}

configure_apache() {
	log_info "Configuring Apache..."

	# Enable required modules
	a2enmod rewrite
	a2enmod headers
	a2enmod env
	a2enmod dir
	a2enmod mime
	a2enmod ssl

	# Get server IP for configuration
	local server_ip
	server_ip=$(hostname -I | awk '{print $1}')

	# Create Apache virtual host
	cat >/etc/apache2/sites-available/nextcloud.conf <<EOF
<VirtualHost *:80>
    ServerName $server_ip
    DocumentRoot /var/www/nextcloud

    <Directory /var/www/nextcloud/>
        Require all granted
        AllowOverride All
        Options FollowSymLinks MultiViews

        <IfModule mod_dav.c>
            Dav off
        </IfModule>
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/nextcloud_error.log
    CustomLog \${APACHE_LOG_DIR}/nextcloud_access.log combined
</VirtualHost>
EOF

	# Enable site and disable default
	a2dissite 000-default.conf
	a2ensite nextcloud.conf

	# Restart Apache
	systemctl restart apache2

	log_success "Apache configured"
}

configure_php() {
	log_info "Configuring PHP..."

	# Find PHP version
	local php_version
	php_version=$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;')
	local php_ini="/etc/php/${php_version}/apache2/php.ini"

	# Backup original
	cp "$php_ini" "${php_ini}.backup"

	# Apply Nextcloud recommended settings
	sed -i 's/memory_limit = .*/memory_limit = 512M/' "$php_ini"
	sed -i 's/upload_max_filesize = .*/upload_max_filesize = 16G/' "$php_ini"
	sed -i 's/post_max_size = .*/post_max_size = 16G/' "$php_ini"
	sed -i 's/max_execution_time = .*/max_execution_time = 360/' "$php_ini"
	sed -i 's/max_input_time = .*/max_input_time = 360/' "$php_ini"
	sed -i 's/;date.timezone.*/date.timezone = Europe\/Warsaw/' "$php_ini"

	# Configure OPcache
	cat >>"$php_ini" <<'EOF'

; Nextcloud OPcache settings
opcache.enable=1
opcache.interned_strings_buffer=16
opcache.max_accelerated_files=10000
opcache.memory_consumption=128
opcache.save_comments=1
opcache.revalidate_freq=1
EOF

	# Configure APCu
	echo "apc.enable_cli=1" >>"/etc/php/${php_version}/mods-available/apcu.ini"

	systemctl restart apache2

	log_success "PHP configured"
}

configure_redis() {
	log_info "Configuring Redis..."

	systemctl enable redis-server
	systemctl start redis-server

	log_success "Redis configured"
}

install_nextcloud() {
	log_info "Installing Nextcloud..."

	local db_password
	db_password=$(cat /root/.nextcloud_db_password)

	if [[ -z $NEXTCLOUD_ADMIN_PASSWORD ]]; then
		prompt_password "Enter Nextcloud admin password" NEXTCLOUD_ADMIN_PASSWORD
	fi

	# Create data directory
	mkdir -p "$NEXTCLOUD_DATA_DIR"
	chown -R www-data:www-data "$NEXTCLOUD_DATA_DIR"

	# Get server IP
	local server_ip
	server_ip=$(hostname -I | awk '{print $1}')

	# Run Nextcloud installer
	cd /var/www/nextcloud
	sudo -u www-data php occ maintenance:install \
		--database "mysql" \
		--database-name "nextcloud" \
		--database-user "nextcloud" \
		--database-pass "$db_password" \
		--admin-user "$NEXTCLOUD_ADMIN_USER" \
		--admin-pass "$NEXTCLOUD_ADMIN_PASSWORD" \
		--data-dir "$NEXTCLOUD_DATA_DIR"

	# Add trusted domain
	sudo -u www-data php occ config:system:set trusted_domains 1 --value="$server_ip"
	sudo -u www-data php occ config:system:set trusted_domains 2 --value="$PI_HOSTNAME"
	sudo -u www-data php occ config:system:set trusted_domains 3 --value="$PI_HOSTNAME.local"

	# Configure Redis caching
	sudo -u www-data php occ config:system:set memcache.local --value='\OC\Memcache\APCu'
	sudo -u www-data php occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'
	sudo -u www-data php occ config:system:set memcache.locking --value='\OC\Memcache\Redis'
	sudo -u www-data php occ config:system:set redis host --value='localhost'
	sudo -u www-data php occ config:system:set redis port --value='6379' --type=integer

	# Set default phone region
	sudo -u www-data php occ config:system:set default_phone_region --value='PL'

	# Enable maintenance window
	sudo -u www-data php occ config:system:set maintenance_window_start --value=1 --type=integer

	log_success "Nextcloud installed"
}

setup_nextcloud_cron() {
	log_info "Setting up Nextcloud background jobs..."

	# Add cron job for background tasks
	crontab -u www-data -l 2>/dev/null || echo "" | crontab -u www-data -
	(
		crontab -u www-data -l 2>/dev/null | grep -v 'nextcloud/cron.php'
		echo "*/5 * * * * php -f /var/www/nextcloud/cron.php"
	) | crontab -u www-data -

	# Switch to cron background job mode
	cd /var/www/nextcloud
	sudo -u www-data php occ background:cron

	log_success "Cron jobs configured"
}

verify_nextcloud() {
	log_info "Verifying Nextcloud installation..."

	local server_ip
	server_ip=$(hostname -I | awk '{print $1}')

	# Check if Nextcloud is responding
	if curl -s -o /dev/null -w "%{http_code}" "http://${server_ip}/status.php" | grep -q "200"; then
		log_success "Nextcloud is responding!"
	else
		log_warning "Nextcloud may not be fully ready. Check manually."
	fi

	# Run Nextcloud check
	cd /var/www/nextcloud
	sudo -u www-data php occ status

	echo
	log_success "========================================"
	log_success "Nextcloud installation complete!"
	log_success "========================================"
	echo
	log_info "Access Nextcloud at: http://${server_ip}"
	log_info "Admin user: $NEXTCLOUD_ADMIN_USER"
	log_info "Database password saved at: /root/.nextcloud_db_password"
	echo
	log_info "Recommended next steps:"
	log_info "1. Set up a domain name pointing to your Pi"
	log_info "2. Configure SSL with: sudo certbot --apache"
	log_info "3. Install Nextcloud apps via the web interface"
	log_info "4. Configure external storage if needed"
}

phase_nextcloud() {
	check_root

	log_info "=== Phase 3: Install Nextcloud ==="

	install_nextcloud_dependencies
	local db_password
	db_password=$(configure_mariadb)
	download_nextcloud
	configure_apache
	configure_php
	configure_redis
	install_nextcloud
	setup_nextcloud_cron
	verify_nextcloud

	log_success "Phase 3 complete!"
}

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

main() {
	local command="${1:-help}"

	case "$command" in
	flash)
		phase_flash
		;;
	flash-remote)
		phase_flash_remote
		;;
	flash-remote-execute)
		phase_flash_remote_execute "${2:-}"
		;;
	configure)
		phase_configure
		;;
	nextcloud)
		phase_nextcloud
		;;
	all-remote)
		phase_all_remote
		;;
	help | --help | -h)
		show_help
		;;
	*)
		log_error "Unknown command: $command"
		show_help
		exit 1
		;;
	esac
}

main "$@"
